from __future__ import annotations

import asyncio
import json
import re
from typing import Literal, TypedDict

from fastapi import HTTPException
from litellm import completion

from app.core.app_config import get_app_config
from app.core.security import decrypt_user_secret, has_usable_user_secret
from app.models.user import User

ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: ChatRole
    content: str


class _ChatCompletionMessage(TypedDict, total=False):
    content: str | None


class _ChatCompletionChoice(TypedDict, total=False):
    message: _ChatCompletionMessage


class _ChatCompletionResponse(TypedDict, total=False):
    choices: list[_ChatCompletionChoice]


JSONMapping = dict[str, object]

LLM_REQUEST_TIMEOUT_SECONDS = 25.0
LLM_MAX_ATTEMPTS_PER_CANDIDATE = 2
LLM_RETRY_BACKOFF_SECONDS = 0.8
JSON_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL | re.IGNORECASE)


def _build_model_candidates(model_name: str) -> list[str]:
    model = model_name.strip()
    if "/" in model:
        return [model]
    return [model, f"openai/{model}", f"deepseek/{model}"]


def _extract_message_content(response: _ChatCompletionResponse) -> str:
    choices = response.get("choices") or []
    if not choices:
        return "{}"
    first_choice = choices[0]
    message = first_choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    return "{}"


def _extract_json_mapping(content: str) -> JSONMapping | None:
    normalized = (content or "").strip()
    if not normalized:
        return None

    candidates = [normalized]
    fenced = JSON_CODE_FENCE_PATTERN.search(normalized)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())

    start = normalized.find("{")
    end = normalized.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidates.append(normalized[start : end + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _resolve_runtime_model_config(user: User) -> tuple[list[str], str, str]:
    app_config = get_app_config()
    custom_model_enabled = is_custom_model_enabled(user)

    if custom_model_enabled:
        model_name = (user.custom_model_name or "").strip()
        api_key = (decrypt_user_secret(user.custom_api_key) or "").strip()
        api_base = user.custom_base_url or str(app_config.default_model.base_url)
    else:
        model_name = app_config.default_model.model
        api_base = str(app_config.default_model.base_url)
        api_key = app_config.default_model.api_key.strip()

    if not api_key:
        raise HTTPException(status_code=500, detail="服务端未配置可用的 LLM API Key")

    return _build_model_candidates(model_name), api_key, api_base


async def _completion_with_timeout(**kwargs: object) -> _ChatCompletionResponse:
    def run_sync_completion() -> _ChatCompletionResponse:
        response = completion(**kwargs)
        return response  # type: ignore[return-value]

    return await asyncio.wait_for(
        asyncio.to_thread(run_sync_completion),
        timeout=LLM_REQUEST_TIMEOUT_SECONDS,
    )


async def _run_completion(
    *,
    messages: list[ChatMessage],
    user: User,
    response_format: dict[str, str] | None = None,
) -> str:
    model_candidates, api_key, api_base = _resolve_runtime_model_config(user)
    last_error: Exception | None = None

    for candidate in model_candidates:
        for attempt in range(LLM_MAX_ATTEMPTS_PER_CANDIDATE):
            try:
                request_kwargs: dict[str, object] = {
                    "model": candidate,
                    "api_key": api_key,
                    "api_base": api_base,
                    "messages": messages,
                    "temperature": 0.7,
                }
                if response_format is not None:
                    request_kwargs["response_format"] = response_format

                response = await _completion_with_timeout(**request_kwargs)
                return (_extract_message_content(response) or "").strip()
            except TimeoutError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc
                if attempt < LLM_MAX_ATTEMPTS_PER_CANDIDATE - 1:
                    await asyncio.sleep(LLM_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if last_error is not None:
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试") from last_error
    raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试")


async def run_json_completion(messages: list[ChatMessage], user: User) -> JSONMapping:
    content = await _run_completion(
        messages=messages,
        user=user,
        response_format={"type": "json_object"},
    )

    parsed = _extract_json_mapping(content)
    if parsed is not None:
        return parsed
    raise HTTPException(status_code=502, detail="AI 返回格式不合法，请稍后重试")


async def run_text_completion(messages: list[ChatMessage], user: User) -> str:
    return await _run_completion(messages=messages, user=user)


def is_custom_model_enabled(user: User) -> bool:
    if user.api_mode != "custom":
        return False
    return bool((user.custom_model_name or "").strip() and has_usable_user_secret(user.custom_api_key))
