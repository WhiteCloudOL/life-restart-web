from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.core.app_config import get_app_config
from app.core.deps import get_current_admin_user, get_session
from app.core.security import has_usable_user_secret
from app.models.user import User
from app.schemas.admin import AdminUserQuotaUpdateRequest, AdminUserRead, PaginatedUsersResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=PaginatedUsersResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
):
    total = session.exec(select(func.count()).select_from(User)).one()
    offset = (page - 1) * size
    users = session.exec(select(User).offset(offset).limit(size)).all()

    items = [
        AdminUserRead(
            id=user.id,
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
        for user in users
    ]

    next_page = page + 1 if offset + size < total else None
    return PaginatedUsersResponse(page=page, size=size, total=total, items=items, next_page=next_page)


@router.put("/users/{user_id}/quota", response_model=AdminUserRead)
def update_user_quota(
    user_id: int,
    payload: AdminUserQuotaUpdateRequest,
    _: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
):
    app_config = get_app_config()
    if payload.world_entry_limit is None and payload.model_call_limit is None:
        raise HTTPException(status_code=400, detail="至少需要提供一个可更新的额度字段")
    if (
        payload.world_entry_limit is not None
        and payload.world_entry_limit > app_config.quota.max_daily_quota
    ):
        raise HTTPException(status_code=400, detail="world_entry_limit 超出系统允许上限")
    if (
        payload.model_call_limit is not None
        and payload.model_call_limit > app_config.quota.max_daily_model_call_limit
    ):
        raise HTTPException(status_code=400, detail="model_call_limit 超出系统允许上限")

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if payload.world_entry_limit is not None:
        user.daily_quota = payload.world_entry_limit
        if user.used_quota_today > user.daily_quota:
            user.used_quota_today = user.daily_quota
    if payload.model_call_limit is not None:
        user.daily_model_call_limit = payload.model_call_limit
        if user.used_model_calls_today > user.daily_model_call_limit:
            user.used_model_calls_today = user.daily_model_call_limit

    session.add(user)
    session.commit()
    session.refresh(user)

    return AdminUserRead(
        id=user.id,
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
