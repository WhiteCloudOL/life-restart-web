import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.app_config import get_app_config
from app.core.world_config import StartupPresetConfig, get_world_config
from app.core.prompt_templates import (
    END_SUMMARY_FALLBACK_TEXT,
    END_SUMMARY_SYSTEM_PROMPT,
    build_end_summary_user_prompt,
)
from app.core.deps import get_current_user, get_session
from app.models.game_session import GameSession
from app.models.preset import Preset
from app.models.user import User
from app.schemas.game import (
    GameForceExitRequest,
    GameForceExitResponse,
    GameNextRequest,
    GameStartRequest,
    GameStepResponse,
    PresetRead,
)
from app.services.game_engine import (
    advance_age,
    apply_effects_to_stats,
    build_next_prompt,
    build_start_prompt,
    ensure_age_stat,
    parse_json_array,
    parse_json_object,
    split_event_into_segments,
    should_force_end_by_death,
    sanitize_llm_json_payload,
)
from app.services.llm import is_custom_model_enabled, run_json_completion, run_text_completion
from app.services.quota import (
    consume_model_call_quota,
    consume_world_entry_quota,
    enforce_model_call_quota,
    enforce_world_entry_quota,
)

router = APIRouter(prefix="/game", tags=["game"])


def _get_configured_preset(preset_id: int) -> StartupPresetConfig:
    world_config = get_world_config()
    custom_preset = world_config.custom_preset
    if custom_preset and custom_preset.enabled and custom_preset.id == preset_id:
        return StartupPresetConfig(
            id=custom_preset.id,
            title=custom_preset.title,
            description=custom_preset.description,
            worldview=custom_preset.default_worldview or "由玩家自定义世界设定",
            character_options=[],
            attributes=custom_preset.attributes,
            max_attribute_points=custom_preset.max_attribute_points,
            start_age=custom_preset.start_age,
            age_step=custom_preset.age_step,
            is_custom=True,
        )
    for preset in world_config.startup_presets:
        if preset.id == preset_id:
            return preset
    raise HTTPException(status_code=404, detail="预设不存在")


def _build_initial_stats(
    preset: StartupPresetConfig,
    payload: GameStartRequest,
) -> dict[str, int]:
    configured_map = {item.key: item for item in preset.attributes}
    allocated = payload.allocated_attributes or {}

    selected_stats: dict[str, int] = {}
    total = 0
    for key, attr in configured_map.items():
        raw_value = allocated.get(key, attr.default_value)
        if not isinstance(raw_value, int):
            raise HTTPException(status_code=400, detail=f"属性 {key} 必须为整数")
        if raw_value < attr.min_value or raw_value > attr.max_value:
            raise HTTPException(
                status_code=400,
                detail=f"属性 {key} 超出允许范围 [{attr.min_value}, {attr.max_value}]",
            )
        selected_stats[key] = raw_value
        total += raw_value

    max_points = _get_preset_points_limit(preset)
    if total > max_points:
        raise HTTPException(
            status_code=400,
            detail=f"属性总和超限，当前 {total}，最大允许 {max_points}",
        )

    unknown_keys = [key for key in allocated.keys() if key not in configured_map]
    if unknown_keys:
        raise HTTPException(status_code=400, detail=f"存在未配置属性: {', '.join(unknown_keys)}")

    return ensure_age_stat(_inject_system_health(selected_stats), start_age=preset.start_age)


def _inject_system_health(stats: dict[str, int]) -> dict[str, int]:
    next_stats = dict(stats)
    physique_candidates = ["体质", "physique", "constitution"]
    for key in physique_candidates:
        value = next_stats.get(key)
        if isinstance(value, (int, float)):
            next_stats["health"] = int(max(0, value))
            return next_stats
    if "health" not in next_stats:
        next_stats["health"] = 100
    return next_stats


def _get_preset_points_limit(preset: StartupPresetConfig) -> int:
    app_total = get_app_config().gameplay.total_attribute_points
    if preset.is_custom:
        return preset.max_attribute_points
    return app_total


def _build_attribute_definitions(preset: StartupPresetConfig) -> list[dict[str, str]]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "purpose": item.purpose,
        }
        for item in preset.attributes
    ]


def _run_story_generation(messages: list[dict[str, str]], user: User) -> tuple[str, dict, bool, list[str], list[str]]:
    last_error: HTTPException | None = None
    for _ in range(2):
        try:
            llm_payload = run_json_completion(messages, user=user)
            event, effects, ended, next_choices = sanitize_llm_json_payload(llm_payload)
            segments = split_event_into_segments(event)
            if event.strip() and len(segments) > 0:
                return event, effects, ended, next_choices, segments
        except HTTPException as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试")


def _build_end_summary(
    *,
    user: User,
    preset_title: str,
    final_stats: dict,
    event_history: list[dict],
    end_reason: str,
) -> str:
    recent_history = event_history[-8:]
    messages = [
        {
            "role": "system",
            "content": END_SUMMARY_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_end_summary_user_prompt(
                preset_title=preset_title,
                end_reason=end_reason,
                final_stats=final_stats,
                recent_history=recent_history,
            ),
        },
    ]
    try:
        summary = run_text_completion(messages, user=user).strip()
        if summary:
            return summary
    except HTTPException:
        pass
    return END_SUMMARY_FALLBACK_TEXT


@router.get("/presets", response_model=List[PresetRead])
def list_presets(
    _: User = Depends(get_current_user),
    __: Session = Depends(get_session),
):
    world_config = get_world_config()
    presets = [
        PresetRead(
            id=preset.id,
            title=preset.title,
            description=preset.description,
            worldview=preset.worldview,
            character_options=preset.character_options,
            max_attribute_points=_get_preset_points_limit(preset),
            is_custom=False,
            attributes=[
                {
                    "key": item.key,
                    "label": item.label,
                    "min_value": item.min_value,
                    "max_value": item.max_value,
                    "default_value": item.default_value,
                }
                for item in preset.attributes
            ],
        )
        for preset in world_config.startup_presets
    ]
    custom_preset = world_config.custom_preset
    if custom_preset and custom_preset.enabled:
        presets.append(
            PresetRead(
                id=custom_preset.id,
                title=custom_preset.title,
                description=custom_preset.description,
                worldview=custom_preset.default_worldview or "自由发挥，随心设定",
                character_options=[],
                max_attribute_points=custom_preset.max_attribute_points,
                is_custom=True,
                attributes=[
                    {
                        "key": item.key,
                        "label": item.label,
                        "min_value": item.min_value,
                        "max_value": item.max_value,
                        "default_value": item.default_value,
                    }
                    for item in custom_preset.attributes
                ],
            )
        )
    return presets


@router.post("/start", response_model=GameStepResponse)
def game_start(
    payload: GameStartRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    preset_config = _get_configured_preset(payload.preset_id)
    preset = session.exec(select(Preset).where(Preset.id == preset_config.id)).first()
    if not preset:
        if preset_config.is_custom:
            initial_stats = {
                item.key: item.default_value
                for item in preset_config.attributes
            }
            preset = Preset(
                id=preset_config.id,
                title=preset_config.title,
                description=preset_config.description,
                initial_stats=json.dumps(initial_stats, ensure_ascii=False),
            )
            session.add(preset)
            session.commit()
            session.refresh(preset)
        else:
            raise HTTPException(status_code=404, detail="预设不存在")

    unlimited = is_custom_model_enabled(current_user)
    # 进入世界才消耗额度（非每次 LLM 调用）
    enforce_world_entry_quota(current_user, unlimited=unlimited)
    enforce_model_call_quota(current_user, unlimited=unlimited)

    selected_setting = (payload.selected_character_setting or "").strip() or None
    preset_worldview = preset_config.worldview
    if preset_config.is_custom:
        preset_worldview = (payload.custom_worldview or "").strip()
        selected_setting = (payload.custom_character_setting or "").strip() or None
        if not preset_worldview:
            raise HTTPException(status_code=400, detail="自定义预设必须填写世界设定")
        if not selected_setting:
            raise HTTPException(status_code=400, detail="自定义预设必须填写角色设定")
    elif selected_setting and selected_setting not in preset_config.character_options:
        raise HTTPException(status_code=400, detail="人物设定不在可选列表中")

    initial_stats = _build_initial_stats(preset_config, payload)
    attribute_definitions = _build_attribute_definitions(preset_config)
    messages = build_start_prompt(
        preset_config.title,
        preset_config.description,
        preset_worldview,
        initial_stats,
        attribute_definitions,
        selected_setting,
        payload.custom_prompt,
    )
    event, effects, ended, next_choices, event_segments = _run_story_generation(messages, current_user)
    story_started = bool(event.strip()) and len(event_segments) > 0
    if not story_started:
        raise HTTPException(status_code=502, detail="AI 未成功推进游戏，请稍后重试")
    next_stats = apply_effects_to_stats(initial_stats, effects)
    next_stats = ensure_age_stat(next_stats, start_age=preset_config.start_age)
    next_stats = _inject_system_health(next_stats)
    death_detected = should_force_end_by_death(event, next_stats)
    ended = ended or death_detected
    if ended:
        next_choices = []
    history = [
        {"role": "system", "content": f"进入世界预设：{preset.title}"},
        {"role": "assistant", "content": event, "effects": effects},
    ]

    game_session = GameSession(
        user_id=current_user.id,
        preset_id=preset.id,
        current_stats=json.dumps(next_stats, ensure_ascii=False),
        event_history=json.dumps(history, ensure_ascii=False),
        is_ended=ended,
    )
    end_reason = "death" if death_detected else ("ended" if ended else None)
    end_summary = None
    if ended:
        end_summary = _build_end_summary(
            user=current_user,
            preset_title=preset.title,
            final_stats=next_stats,
            event_history=history,
            end_reason=end_reason or "ended",
        )
        history.append({"role": "assistant", "content": end_summary, "effects": {}})
        game_session.event_history = json.dumps(history, ensure_ascii=False)

    # 只有正式成功开始游戏后，才计入一次“进入世界”
    consume_world_entry_quota(current_user, unlimited=unlimited)
    consume_model_call_quota(current_user, unlimited=unlimited)
    session.add(game_session)
    session.add(current_user)
    session.commit()
    session.refresh(game_session)
    session.refresh(current_user)

    return GameStepResponse(
        session_id=game_session.id,
        event=event,
        event_segments=event_segments,
        current_stats=next_stats,
        is_ended=game_session.is_ended,
        world_entry_limit=current_user.daily_quota,
        world_entries_used_today=current_user.used_quota_today,
        model_call_limit=current_user.daily_model_call_limit,
        model_calls_used_today=current_user.used_model_calls_today,
        next_choices=next_choices,
        end_reason=end_reason,
        end_summary=end_summary,
    )


@router.post("/next", response_model=GameStepResponse)
def game_next(
    payload: GameNextRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # 防越权（IDOR）核心逻辑：
    # 必须同时匹配 session_id 与 current_user.id，禁止访问他人会话
    game_session = session.exec(
        select(GameSession).where(
            GameSession.id == payload.session_id,
            GameSession.user_id == current_user.id,
        )
    ).first()
    if not game_session:
        raise HTTPException(status_code=404, detail="会话不存在或无访问权限")
    if game_session.is_ended:
        raise HTTPException(status_code=400, detail="该会话已结束")
    preset_config = _get_configured_preset(game_session.preset_id)
    unlimited = is_custom_model_enabled(current_user)
    enforce_model_call_quota(current_user, unlimited=unlimited)

    current_stats = ensure_age_stat(
        parse_json_object(game_session.current_stats),
        start_age=preset_config.start_age,
    )
    event_history = parse_json_array(game_session.event_history)

    messages = build_next_prompt(current_stats, event_history, payload.user_choice)
    event, effects, ended, next_choices, event_segments = _run_story_generation(messages, current_user)

    # 属性变更必须后端计算，防止客户端篡改
    next_stats = apply_effects_to_stats(current_stats, effects)
    next_stats = advance_age(next_stats, age_step=preset_config.age_step)
    next_stats = _inject_system_health(next_stats)
    death_detected = should_force_end_by_death(event, next_stats)
    ended = ended or death_detected
    if ended:
        next_choices = []

    event_history.append({"role": "user", "content": payload.user_choice})
    event_history.append({"role": "assistant", "content": event, "effects": effects})
    end_reason = "death" if death_detected else ("ended" if ended else None)
    end_summary = None
    if ended:
        end_summary = _build_end_summary(
            user=current_user,
            preset_title=preset_config.title,
            final_stats=next_stats,
            event_history=event_history,
            end_reason=end_reason or "ended",
        )
        event_history.append({"role": "assistant", "content": end_summary, "effects": {}})

    game_session.current_stats = json.dumps(next_stats, ensure_ascii=False)
    game_session.event_history = json.dumps(event_history, ensure_ascii=False)
    game_session.is_ended = ended

    # 成功后才计数（失败不计数）
    consume_model_call_quota(current_user, unlimited=unlimited)
    session.add(game_session)
    session.add(current_user)
    session.commit()
    session.refresh(game_session)
    session.refresh(current_user)

    return GameStepResponse(
        session_id=game_session.id,
        event=event,
        event_segments=event_segments,
        current_stats=next_stats,
        is_ended=game_session.is_ended,
        world_entry_limit=current_user.daily_quota,
        world_entries_used_today=current_user.used_quota_today,
        model_call_limit=current_user.daily_model_call_limit,
        model_calls_used_today=current_user.used_model_calls_today,
        next_choices=next_choices,
        end_reason=end_reason,
        end_summary=end_summary,
    )


@router.post("/force-exit", response_model=GameForceExitResponse)
def force_exit_game(
    payload: GameForceExitRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    game_session = session.exec(
        select(GameSession).where(
            GameSession.id == payload.session_id,
            GameSession.user_id == current_user.id,
        )
    ).first()
    if not game_session:
        raise HTTPException(status_code=404, detail="会话不存在或无访问权限")
    current_stats = parse_json_object(game_session.current_stats)
    event_history = parse_json_array(game_session.event_history)
    preset_config = _get_configured_preset(game_session.preset_id)
    end_summary = _build_end_summary(
        user=current_user,
        preset_title=preset_config.title,
        final_stats=current_stats,
        event_history=event_history,
        end_reason="forced_exit",
    )
    event_history.append({"role": "assistant", "content": end_summary, "effects": {}})
    game_session.event_history = json.dumps(event_history, ensure_ascii=False)
    game_session.is_ended = True
    session.add(game_session)
    session.commit()
    return GameForceExitResponse(success=True, end_reason="forced_exit", end_summary=end_summary)
