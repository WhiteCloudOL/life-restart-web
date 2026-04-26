import json
import re
from typing import Any, Dict, List

from app.core.app_config import get_app_config
from app.core.prompt_templates import (
    GAME_ENGINE_SYSTEM_PROMPT,
    build_next_user_prompt,
    build_start_user_prompt,
)

PHYSIQUE_DEATH_KEYS = {"体质", "physique", "constitution"}


def parse_json_object(data: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(data)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def parse_json_array(data: str) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(data)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def build_start_prompt(
    preset_title: str,
    preset_description: str,
    preset_worldview: str,
    initial_stats: Dict[str, Any],
    attribute_definitions: List[Dict[str, str]] | None,
    selected_character_setting: str | None,
    custom_prompt: str | None,
) -> List[Dict[str, str]]:
    character_setting = selected_character_setting or "未指定"
    user_hint = (custom_prompt or "").strip() or "无"
    definitions = attribute_definitions or []
    return [
        {
            "role": "system",
            "content": GAME_ENGINE_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_start_user_prompt(
                preset_title=preset_title,
                preset_description=preset_description,
                preset_worldview=preset_worldview,
                character_setting=character_setting,
                attribute_definitions=definitions,
                initial_stats=initial_stats,
                user_hint=user_hint,
            ),
        },
    ]


def build_next_prompt(
    current_stats: Dict[str, Any],
    event_history: List[Dict[str, Any]],
    user_choice: str,
) -> List[Dict[str, str]]:
    # 截取最近记录避免 prompt 过长
    recent_history = event_history[-10:]
    return [
        {
            "role": "system",
            "content": GAME_ENGINE_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_next_user_prompt(
                current_stats=current_stats,
                recent_history=recent_history,
                user_choice=user_choice,
            ),
        },
    ]


def _sanitize_next_choices(raw_choices: Any, ended: bool) -> List[str]:
    app_config = get_app_config()
    fallback_choices = app_config.gameplay.default_next_choices
    max_choices = app_config.gameplay.max_next_choices

    if ended:
        return []

    if not isinstance(raw_choices, list):
        return fallback_choices

    cleaned: List[str] = []
    for item in raw_choices:
        if not isinstance(item, str):
            continue
        choice = item.strip()
        if not choice:
            continue
        if len(choice) > 180:
            choice = choice[:180]
        if choice in cleaned:
            continue
        cleaned.append(choice)
        if len(cleaned) >= max_choices:
            break

    if len(cleaned) != 3:
        return fallback_choices
    return cleaned


def sanitize_llm_json_payload(payload: Dict[str, Any]) -> tuple[str, Dict[str, Any], bool, List[str]]:
    event = str(payload.get("event", "故事继续推进。")).strip() or "故事继续推进。"
    effects_raw = payload.get("effects", {})
    effects: Dict[str, Any] = effects_raw if isinstance(effects_raw, dict) else {}
    ended = bool(payload.get("ended", False))
    next_choices = _sanitize_next_choices(payload.get("next_choices"), ended)
    return event, effects, ended, next_choices


def should_force_end_by_death(event: str, stats: Dict[str, Any]) -> bool:
    app_config = get_app_config()
    normalized_event = (event or "").lower()
    for keyword in app_config.gameplay.death_event_keywords:
        key = keyword.strip().lower()
        if key and key in normalized_event:
            return True

    threshold = app_config.gameplay.death_stat_threshold
    for stat_key in app_config.gameplay.death_stat_keys:
        if stat_key in PHYSIQUE_DEATH_KEYS:
            continue
        value = stats.get(stat_key)
        if isinstance(value, (int, float)) and value <= threshold:
            return True
    return False


def split_event_into_segments(event: str) -> List[str]:
    """
    将一次性大段文本拆成短段，便于前端逐段展示。
    优先按自然段拆分；若缺少换行，再按句号等标点分块。
    """
    normalized = (event or "").replace("\r\n", "\n").strip()
    if not normalized:
        return ["故事继续推进。"]

    paragraphs = [part.strip() for part in re.split(r"\n{1,}", normalized) if part.strip()]
    if len(paragraphs) >= 2:
        return paragraphs

    sentences = re.split(r"(?<=[。！？!?])", normalized)
    chunks: List[str] = []
    bucket = ""
    for sentence in sentences:
        piece = sentence.strip()
        if not piece:
            continue
        if not bucket:
            bucket = piece
            continue
        if len(bucket) + len(piece) <= 80:
            bucket += piece
        else:
            chunks.append(bucket)
            bucket = piece

    if bucket:
        chunks.append(bucket)
    return chunks if chunks else [normalized]


def apply_effects_to_stats(current_stats: Dict[str, Any], effects: Dict[str, Any]) -> Dict[str, Any]:
    """
    核心安全点：
    后端统一计算数值变化，不信任前端传入的任何属性结果，避免篡改。
    """
    next_stats = dict(current_stats)
    for key, delta in effects.items():
        # 年龄由系统节奏统一推进，避免模型返回的 effects 直接篡改年龄节奏。
        if key == "age":
            continue
        if not isinstance(delta, (int, float)):
            continue
        current_value = next_stats.get(key, 0)
        if isinstance(current_value, (int, float)):
            next_stats[key] = current_value + delta
        else:
            next_stats[key] = delta
    return next_stats


def ensure_age_stat(stats: Dict[str, Any], start_age: int = 18) -> Dict[str, Any]:
    next_stats = dict(stats)
    current_age = next_stats.get("age")
    if isinstance(current_age, (int, float)):
        next_stats["age"] = max(0, int(current_age))
        return next_stats
    next_stats["age"] = max(0, int(start_age))
    return next_stats


def advance_age(stats: Dict[str, Any], age_step: int = 1) -> Dict[str, Any]:
    next_stats = ensure_age_stat(stats)
    step = max(0, int(age_step))
    next_stats["age"] = max(0, int(next_stats.get("age", 0)) + step)
    return next_stats
