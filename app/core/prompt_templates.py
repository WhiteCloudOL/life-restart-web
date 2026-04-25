import json
from typing import Any

GAME_ENGINE_SYSTEM_PROMPT = (
    "你是人生重开模拟器引擎。"
    "你必须返回 JSON 对象，字段固定为："
    "event(string), effects(object), ended(boolean), next_choices(string[])。"
    "event 必须是一次性推进的大段剧情，长度建议 260-700 字，拆成 3-7 个自然段（段落用换行分隔）。"
    "严禁输出 Markdown、代码块和解释文字。"
    "effects 只允许返回数值增减，如 {\"health\": -2, \"wealth\": 3}。"
    "当前属性中的 age 表示当前年龄，剧情推进必须与年龄阶段相符。"
    "next_choices 必须且只能提供 3 条，按顺序对应高风险/中风险/低风险。"
    "每条选项都要包含行动、收益、风险，并明确都存在人生终局可能。"
    "高风险：高收益且高概率重创，可能直接结束人生。"
    "中风险：中收益中风险，策略失误会导致严重后果。"
    "低风险：低收益低风险，但在累积失误或外部灾难下仍可能终局。"
)

END_SUMMARY_SYSTEM_PROMPT = (
    "你是人生模拟总结助手。"
    "请用简体中文输出一段 120-220 字的结局总结。"
    "要求：1）概括关键转折 2）评价角色特质与代价 3）给出一句后续建议。"
    "仅输出纯文本，不要 Markdown。"
)

END_SUMMARY_FALLBACK_TEXT = (
    "这一生在关键抉择与外部冲击中走到了终点。你展现了鲜明的性格与行动力，也为部分冒险付出了代价。"
    "若再次启程，建议围绕核心短板提前布局，在高风险机会前先准备兜底资源。"
)


def build_start_user_prompt(
    *,
    preset_title: str,
    preset_description: str,
    preset_worldview: str,
    character_setting: str,
    attribute_definitions: list[dict[str, str]],
    initial_stats: dict[str, Any],
    user_hint: str,
) -> str:
    return (
        f"世界预设标题: {preset_title}\n"
        f"世界预设描述: {preset_description}\n"
        f"世界观设定: {preset_worldview}\n"
        f"人物设定: {character_setting}\n"
        f"属性定义(仅用于理解作用): {json.dumps(attribute_definitions, ensure_ascii=False)}\n"
        f"初始属性: {json.dumps(initial_stats, ensure_ascii=False)}\n"
        f"玩家自定义提示词: {user_hint}\n"
        "请输出开局事件，必须一次性推进一大段剧情，并留出可选择分支。"
    )


def build_next_user_prompt(
    *,
    current_stats: dict[str, Any],
    recent_history: list[dict[str, Any]],
    user_choice: str,
) -> str:
    return (
        f"当前属性: {json.dumps(current_stats, ensure_ascii=False)}\n"
        f"最近事件历史: {json.dumps(recent_history, ensure_ascii=False)}\n"
        f"用户选择: {user_choice}\n"
        "请推进下一回合，必须一次性推进一大段剧情，并留出可选择分支。"
    )


def build_end_summary_user_prompt(
    *,
    preset_title: str,
    end_reason: str,
    final_stats: dict[str, Any],
    recent_history: list[dict[str, Any]],
) -> str:
    return (
        f"世界: {preset_title}\n"
        f"结束原因: {end_reason}\n"
        f"最终属性: {json.dumps(final_stats, ensure_ascii=False)}\n"
        f"最近事件: {json.dumps(recent_history, ensure_ascii=False)}"
    )
