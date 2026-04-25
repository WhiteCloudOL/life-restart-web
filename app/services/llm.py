import json
from typing import Any, Dict, List

from fastapi import HTTPException
from litellm import completion

from app.core.app_config import get_app_config
from app.core.security import decrypt_user_secret, has_usable_user_secret
from app.models.user import User


def _build_model_candidates(model_name: str) -> List[str]:
    """
    兼容未填写 provider 前缀的模型名。
    对裸模型名依次尝试:
    - 原始模型名
    - openai/{model}
    - deepseek/{model}
    """
    model = model_name.strip()
    if "/" in model:
        return [model]
    return [model, f"openai/{model}", f"deepseek/{model}"]


def _extract_message_content(resp: Any) -> str:
    try:
        return resp.choices[0].message.content or "{}"
    except (AttributeError, IndexError, KeyError, TypeError):
        return "{}"


def run_json_completion(
    messages: List[Dict[str, str]],
    user: User,
) -> Dict[str, Any]:
    app_config = get_app_config()
    custom_model_enabled = is_custom_model_enabled(user)

    if custom_model_enabled:
        model_name = user.custom_model_name.strip()
        api_key = (decrypt_user_secret(user.custom_api_key) or "").strip()
        api_base = user.custom_base_url or str(app_config.default_model.base_url)
    else:
        model_name = app_config.default_model.model
        api_base = str(app_config.default_model.base_url)
        api_key = app_config.default_model.api_key.strip()

    model_candidates = _build_model_candidates(model_name)

    if not api_key:
        raise HTTPException(status_code=500, detail="服务端未配置可用的 LLM API Key")

    try:
        last_error: Exception | None = None
        resp = None
        for candidate in model_candidates:
            try:
                resp = completion(
                    model=candidate,
                    api_key=api_key,
                    api_base=api_base,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )
                break
            except Exception as exc:
                last_error = exc
                continue

        if resp is None:
            assert last_error is not None
            raise last_error

        content = _extract_message_content(resp)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM 返回内容不是 JSON object")
        return parsed
    except HTTPException:
        raise
    except Exception:
        # 避免把上游细节泄露给客户端
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试")


def run_text_completion(
    messages: List[Dict[str, str]],
    user: User,
) -> str:
    app_config = get_app_config()
    custom_model_enabled = is_custom_model_enabled(user)

    if custom_model_enabled:
        model_name = user.custom_model_name.strip()
        api_key = (decrypt_user_secret(user.custom_api_key) or "").strip()
        api_base = user.custom_base_url or str(app_config.default_model.base_url)
    else:
        model_name = app_config.default_model.model
        api_base = str(app_config.default_model.base_url)
        api_key = app_config.default_model.api_key.strip()

    model_candidates = _build_model_candidates(model_name)
    if not api_key:
        raise HTTPException(status_code=500, detail="服务端未配置可用的 LLM API Key")

    try:
        last_error: Exception | None = None
        resp = None
        for candidate in model_candidates:
            try:
                resp = completion(
                    model=candidate,
                    api_key=api_key,
                    api_base=api_base,
                    messages=messages,
                    temperature=0.7,
                )
                break
            except Exception as exc:
                last_error = exc
                continue

        if resp is None:
            assert last_error is not None
            raise last_error

        return (_extract_message_content(resp) or "").strip()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试")


def is_custom_model_enabled(user: User) -> bool:
    """
    自定义模型生效条件：
    - 用户提供了 custom_model_name
    - 用户提供了 custom_api_key
    符合后即视为“自定义模型调用”，业务上不限额。
    """
    if user.api_mode != "custom":
        return False
    return bool((user.custom_model_name or "").strip() and has_usable_user_secret(user.custom_api_key))
