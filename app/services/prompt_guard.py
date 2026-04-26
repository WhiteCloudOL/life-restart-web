from __future__ import annotations

import re

from fastapi import HTTPException

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
MULTI_SPACE_PATTERN = re.compile(r"\s+")
PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all|the)?\s*previous\s+instructions?", re.IGNORECASE),
    re.compile(r"忽略(所有|之前|以上).{0,12}(指令|要求|规则)"),
    re.compile(r"(system|developer)\s*prompt", re.IGNORECASE),
    re.compile(r"(越狱|jailbreak|dan模式|dan mode)", re.IGNORECASE),
    re.compile(r"(输出|泄露|显示).{0,12}(提示词|system prompt|developer prompt)", re.IGNORECASE),
    re.compile(r"(你现在不是|现在开始扮演).{0,20}(系统|开发者|管理员)"),
)


def sanitize_user_prompt_input(*, field_name: str, value: str | None, max_length: int, allow_empty: bool) -> str:
    raw_value = (value or "").strip()
    normalized = CONTROL_CHAR_PATTERN.sub("", raw_value)
    normalized = MULTI_SPACE_PATTERN.sub(" ", normalized).strip()

    if not normalized:
        if allow_empty:
            return ""
        raise HTTPException(status_code=400, detail=f"{field_name} 不能为空")

    if len(normalized) > max_length:
        raise HTTPException(status_code=400, detail=f"{field_name} 超出最大长度限制")

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(normalized):
            raise HTTPException(status_code=400, detail=f"{field_name} 包含高风险提示注入内容，已被拒绝")

    return normalized
