from __future__ import annotations

import json

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.app_config import get_app_config
from app.core.prompt_templates import (
    END_SUMMARY_FALLBACK_TEXT,
    END_SUMMARY_SYSTEM_PROMPT,
    build_end_summary_user_prompt,
)
from app.core.world_config import StartupPresetConfig, get_world_config
from app.models.game_session import GameSession
from app.models.preset import Preset
from app.models.user import User
from app.repositories.game_session_repository import GameSessionRepository
from app.repositories.preset_repository import PresetRepository
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
    sanitize_llm_json_payload,
    should_force_end_by_death,
    split_event_into_segments,
)
from app.services.llm import ChatMessage, is_custom_model_enabled, run_json_completion, run_text_completion
from app.services.prompt_guard import sanitize_user_prompt_input
from app.services.quota import (
    consume_model_call_quota,
    consume_world_entry_quota,
    enforce_model_call_quota,
    enforce_world_entry_quota,
)


class GameApplicationService:
    """游戏应用服务。

    这里负责跨配置、额度、Prompt、LLM、仓储的编排。
    Router 只做依赖注入与调用转发。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.preset_repository = PresetRepository(session)
        self.game_session_repository = GameSessionRepository(session)

    async def list_presets(self) -> list[PresetRead]:
        world_config = get_world_config()
        presets = [
            PresetRead(
                id=preset.id,
                title=preset.title,
                description=preset.description,
                worldview=preset.worldview,
                character_options=preset.character_options,
                max_attribute_points=self._get_preset_points_limit(preset),
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

    async def start_game(self, payload: GameStartRequest, current_user: User) -> GameStepResponse:
        preset_config = self._get_configured_preset(payload.preset_id)
        preset = await self.preset_repository.get_by_id(preset_config.id)
        if preset is None:
            if not preset_config.is_custom:
                raise HTTPException(status_code=404, detail="预设不存在")
            preset = await self._create_custom_preset_record(preset_config)

        unlimited = is_custom_model_enabled(current_user)
        enforce_world_entry_quota(current_user, unlimited=unlimited)
        enforce_model_call_quota(current_user, unlimited=unlimited)

        selected_setting, worldview, custom_hint = self._normalize_start_inputs(payload, preset_config)
        initial_stats = self._build_initial_stats(preset_config, payload)
        attribute_definitions = self._build_attribute_definitions(preset_config)
        messages = build_start_prompt(
            preset_title=preset_config.title,
            preset_description=preset_config.description,
            preset_worldview=worldview,
            initial_stats=initial_stats,
            attribute_definitions=attribute_definitions,
            selected_character_setting=selected_setting,
            custom_prompt=custom_hint,
        )

        event, effects, ended, next_choices, event_segments = await self._run_story_generation(messages, current_user)
        next_stats = ensure_age_stat(apply_effects_to_stats(initial_stats, effects), start_age=preset_config.start_age)
        next_stats = self._inject_system_health(next_stats)
        death_detected = should_force_end_by_death(event, next_stats)
        ended = ended or death_detected
        if ended:
            next_choices = []

        history: list[dict[str, object]] = [
            {"role": "system", "content": f"进入世界预设：{preset.title}"},
            {"role": "assistant", "content": event, "effects": effects},
        ]

        game_session = GameSession(
            user_id=self._require_user_id(current_user),
            preset_id=self._require_preset_id(preset),
            current_stats=json.dumps(next_stats, ensure_ascii=False),
            event_history=json.dumps(history, ensure_ascii=False),
            is_ended=ended,
        )

        end_reason = "death" if death_detected else ("ended" if ended else None)
        end_summary: str | None = None
        if ended:
            end_summary = await self._build_end_summary(
                user=current_user,
                preset_title=preset.title,
                final_stats=next_stats,
                event_history=history,
                end_reason=end_reason or "ended",
            )
            history.append({"role": "assistant", "content": end_summary, "effects": {}})
            game_session.event_history = json.dumps(history, ensure_ascii=False)

        consume_world_entry_quota(current_user, unlimited=unlimited)
        consume_model_call_quota(current_user, unlimited=unlimited)
        self.session.add(current_user)
        persisted_session = await self.game_session_repository.save(game_session)
        await self.session.refresh(current_user)

        return GameStepResponse(
            session_id=self._require_game_session_id(persisted_session),
            event=event,
            event_segments=event_segments,
            current_stats=next_stats,
            is_ended=persisted_session.is_ended,
            world_entry_limit=current_user.daily_quota,
            world_entries_used_today=current_user.used_quota_today,
            model_call_limit=current_user.daily_model_call_limit,
            model_calls_used_today=current_user.used_model_calls_today,
            next_choices=next_choices,
            end_reason=end_reason,
            end_summary=end_summary,
        )

    async def advance_game(self, payload: GameNextRequest, current_user: User) -> GameStepResponse:
        game_session = await self.game_session_repository.get_owned_session(
            session_id=payload.session_id,
            user_id=self._require_user_id(current_user),
        )
        if game_session is None:
            raise HTTPException(status_code=404, detail="会话不存在或无访问权限")
        if game_session.is_ended:
            raise HTTPException(status_code=400, detail="该会话已结束")

        preset_config = self._get_configured_preset(game_session.preset_id)
        unlimited = is_custom_model_enabled(current_user)
        enforce_model_call_quota(current_user, unlimited=unlimited)

        user_choice = sanitize_user_prompt_input(
            field_name="用户行动",
            value=payload.user_choice,
            max_length=500,
            allow_empty=False,
        )
        current_stats = ensure_age_stat(parse_json_object(game_session.current_stats), start_age=preset_config.start_age)
        event_history = parse_json_array(game_session.event_history)
        messages = build_next_prompt(current_stats=current_stats, event_history=event_history, user_choice=user_choice)
        event, effects, ended, next_choices, event_segments = await self._run_story_generation(messages, current_user)

        next_stats = apply_effects_to_stats(current_stats, effects)
        next_stats = advance_age(next_stats, age_step=preset_config.age_step)
        next_stats = self._inject_system_health(next_stats)
        death_detected = should_force_end_by_death(event, next_stats)
        ended = ended or death_detected
        if ended:
            next_choices = []

        event_history.append({"role": "user", "content": user_choice})
        event_history.append({"role": "assistant", "content": event, "effects": effects})
        end_reason = "death" if death_detected else ("ended" if ended else None)
        end_summary: str | None = None
        if ended:
            end_summary = await self._build_end_summary(
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

        consume_model_call_quota(current_user, unlimited=unlimited)
        self.session.add(current_user)
        persisted_session = await self.game_session_repository.save(game_session)
        await self.session.refresh(current_user)

        return GameStepResponse(
            session_id=self._require_game_session_id(persisted_session),
            event=event,
            event_segments=event_segments,
            current_stats=next_stats,
            is_ended=persisted_session.is_ended,
            world_entry_limit=current_user.daily_quota,
            world_entries_used_today=current_user.used_quota_today,
            model_call_limit=current_user.daily_model_call_limit,
            model_calls_used_today=current_user.used_model_calls_today,
            next_choices=next_choices,
            end_reason=end_reason,
            end_summary=end_summary,
        )

    async def force_exit_game(self, payload: GameForceExitRequest, current_user: User) -> GameForceExitResponse:
        game_session = await self.game_session_repository.get_owned_session(
            session_id=payload.session_id,
            user_id=self._require_user_id(current_user),
        )
        if game_session is None:
            raise HTTPException(status_code=404, detail="会话不存在或无访问权限")

        current_stats = parse_json_object(game_session.current_stats)
        event_history = parse_json_array(game_session.event_history)
        preset_config = self._get_configured_preset(game_session.preset_id)
        end_summary = await self._build_end_summary(
            user=current_user,
            preset_title=preset_config.title,
            final_stats=current_stats,
            event_history=event_history,
            end_reason="forced_exit",
        )
        event_history.append({"role": "assistant", "content": end_summary, "effects": {}})
        game_session.event_history = json.dumps(event_history, ensure_ascii=False)
        game_session.is_ended = True
        await self.game_session_repository.save(game_session)
        return GameForceExitResponse(success=True, end_reason="forced_exit", end_summary=end_summary)

    async def _create_custom_preset_record(self, preset_config: StartupPresetConfig) -> Preset:
        initial_stats = {item.key: item.default_value for item in preset_config.attributes}
        preset = Preset(
            id=preset_config.id,
            title=preset_config.title,
            description=preset_config.description,
            initial_stats=json.dumps(initial_stats, ensure_ascii=False),
        )
        return await self.preset_repository.save(preset)

    def _normalize_start_inputs(
        self,
        payload: GameStartRequest,
        preset_config: StartupPresetConfig,
    ) -> tuple[str | None, str, str | None]:
        selected_setting = (payload.selected_character_setting or "").strip() or None
        preset_worldview = preset_config.worldview
        custom_hint_raw = (payload.custom_prompt or "").strip()
        custom_hint = None
        if custom_hint_raw:
            custom_hint = sanitize_user_prompt_input(
                field_name="自定义提示词",
                value=custom_hint_raw,
                max_length=200,
                allow_empty=True,
            )

        if preset_config.is_custom:
            preset_worldview = sanitize_user_prompt_input(
                field_name="自定义世界设定",
                value=payload.custom_worldview,
                max_length=2000,
                allow_empty=False,
            )
            selected_setting = sanitize_user_prompt_input(
                field_name="自定义角色设定",
                value=payload.custom_character_setting,
                max_length=500,
                allow_empty=False,
            )
        elif selected_setting and selected_setting not in preset_config.character_options:
            raise HTTPException(status_code=400, detail="人物设定不在可选列表中")

        return selected_setting, preset_worldview, custom_hint

    async def _run_story_generation(
        self,
        messages: list[ChatMessage],
        user: User,
    ) -> tuple[str, dict[str, object], bool, list[str], list[str]]:
        last_error: HTTPException | None = None
        for _ in range(2):
            try:
                llm_payload = await run_json_completion(messages, user=user)
                event, effects, ended, next_choices = sanitize_llm_json_payload(llm_payload)
                segments = split_event_into_segments(event)
                if event.strip() and segments:
                    return event, effects, ended, next_choices, segments
            except HTTPException as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试")

    async def _build_end_summary(
        self,
        *,
        user: User,
        preset_title: str,
        final_stats: dict[str, object],
        event_history: list[dict[str, object]],
        end_reason: str,
    ) -> str:
        recent_history = event_history[-8:]
        messages: list[ChatMessage] = [
            {"role": "system", "content": END_SUMMARY_SYSTEM_PROMPT},
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
            summary = (await run_text_completion(messages, user=user)).strip()
            if summary:
                return summary
        except HTTPException:
            pass
        return END_SUMMARY_FALLBACK_TEXT

    @staticmethod
    def _inject_system_health(stats: dict[str, int]) -> dict[str, int]:
        next_stats = dict(stats)
        for key in ("体质", "physique", "constitution"):
            value = next_stats.get(key)
            if isinstance(value, (int, float)):
                next_stats["health"] = int(max(1, value))
                return next_stats
        if "health" not in next_stats:
            next_stats["health"] = 100
        return next_stats

    @staticmethod
    def _build_attribute_definitions(preset: StartupPresetConfig) -> list[dict[str, str]]:
        return [{"key": item.key, "label": item.label, "purpose": item.purpose} for item in preset.attributes]

    def _build_initial_stats(self, preset: StartupPresetConfig, payload: GameStartRequest) -> dict[str, int]:
        configured_map = {item.key: item for item in preset.attributes}
        allocated = payload.allocated_attributes or {}
        selected_stats: dict[str, int] = {}
        total_points = 0

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
            total_points += raw_value

        max_points = self._get_preset_points_limit(preset)
        if total_points > max_points:
            raise HTTPException(
                status_code=400,
                detail=f"属性总和超限，当前 {total_points}，最大允许 {max_points}",
            )

        unknown_keys = [key for key in allocated.keys() if key not in configured_map]
        if unknown_keys:
            raise HTTPException(status_code=400, detail=f"存在未配置属性: {', '.join(unknown_keys)}")

        return ensure_age_stat(self._inject_system_health(selected_stats), start_age=preset.start_age)

    def _get_preset_points_limit(self, preset: StartupPresetConfig) -> int:
        if preset.is_custom:
            return preset.max_attribute_points
        return get_app_config().gameplay.total_attribute_points

    @staticmethod
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

    @staticmethod
    def _require_user_id(user: User) -> int:
        if user.id is None:
            raise HTTPException(status_code=500, detail="用户状态异常，缺少用户标识")
        return user.id

    @staticmethod
    def _require_preset_id(preset: Preset) -> int:
        if preset.id is None:
            raise HTTPException(status_code=500, detail="预设状态异常，缺少预设标识")
        return preset.id

    @staticmethod
    def _require_game_session_id(game_session: GameSession) -> int:
        if game_session.id is None:
            raise HTTPException(status_code=500, detail="会话状态异常，缺少会话标识")
        return game_session.id
