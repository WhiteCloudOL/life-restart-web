from __future__ import annotations

from app.core.security import has_usable_user_secret
from app.models.user import User
from app.schemas.admin import AdminUserRead
from app.schemas.user import UserRead


def to_user_read(user: User) -> UserRead:
    nickname = (user.nickname or "").strip() or user.username
    return UserRead(
        id=_require_user_id(user),
        username=user.username,
        nickname=nickname,
        api_mode=user.api_mode if user.api_mode in {"default", "custom"} else "default",
        has_custom_api_key=has_usable_user_secret(user.custom_api_key),
        custom_model_name=user.custom_model_name,
        custom_base_url=user.custom_base_url,
        is_admin=user.is_admin,
        world_entry_limit=user.daily_quota,
        world_entries_used_today=user.used_quota_today,
        model_call_limit=user.daily_model_call_limit,
        model_calls_used_today=user.used_model_calls_today,
        last_active_date=user.last_active_date,
    )


def to_admin_user_read(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=_require_user_id(user),
        username=user.username,
        nickname=(user.nickname or "").strip() or user.username,
        api_mode=user.api_mode if user.api_mode in {"default", "custom"} else "default",
        is_admin=user.is_admin,
        world_entry_limit=user.daily_quota,
        world_entries_used_today=user.used_quota_today,
        model_call_limit=user.daily_model_call_limit,
        model_calls_used_today=user.used_model_calls_today,
        last_active_date=user.last_active_date,
        has_custom_api_key=has_usable_user_secret(user.custom_api_key),
    )


def _require_user_id(user: User) -> int:
    if user.id is None:
        raise ValueError("用户缺少主键标识")
    return user.id
