from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.core.app_config import get_app_config
from app.core.deps import get_current_admin_user, get_session
from app.core.security import has_usable_user_secret, hash_password
from app.models.game_session import GameSession
from app.models.user import User
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserQuotaUpdateRequest,
    AdminUserRead,
    AdminUserUpdateRequest,
    PaginatedUsersResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_admin_user_read(user: User) -> AdminUserRead:
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


def _admin_count(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User).where(User.is_admin == True)).one()


def _validate_limits(*, world_entry_limit: int | None, model_call_limit: int | None) -> None:
    app_config = get_app_config()
    if world_entry_limit is not None and world_entry_limit > app_config.quota.max_daily_quota:
        raise HTTPException(status_code=400, detail="world_entry_limit 超出系统允许上限")
    if (
        model_call_limit is not None
        and model_call_limit > app_config.quota.max_daily_model_call_limit
    ):
        raise HTTPException(status_code=400, detail="model_call_limit 超出系统允许上限")


def _apply_user_limits(*, user: User, world_entry_limit: int | None, model_call_limit: int | None) -> None:
    if world_entry_limit is not None:
        user.daily_quota = world_entry_limit
        if user.used_quota_today > user.daily_quota:
            user.used_quota_today = user.daily_quota
    if model_call_limit is not None:
        user.daily_model_call_limit = model_call_limit
        if user.used_model_calls_today > user.daily_model_call_limit:
            user.used_model_calls_today = user.daily_model_call_limit


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
    items = [_to_admin_user_read(user) for user in users]
    next_page = page + 1 if offset + size < total else None
    return PaginatedUsersResponse(page=page, size=size, total=total, items=items, next_page=next_page)


@router.post("/users", response_model=AdminUserRead, status_code=201)
def create_user(
    payload: AdminUserCreateRequest,
    _: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
):
    existing_user = session.exec(select(User).where(User.username == payload.username)).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="用户名已存在")

    app_config = get_app_config()
    user = User(
        username=payload.username,
        nickname=payload.nickname or payload.username,
        hashed_password=hash_password(payload.password),
        is_admin=payload.is_admin,
        daily_quota=app_config.quota.default_daily_quota,
        daily_model_call_limit=app_config.quota.default_daily_model_call_limit,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_admin_user_read(user)


@router.put("/users/{user_id}/quota", response_model=AdminUserRead)
def update_user_quota(
    user_id: int,
    payload: AdminUserQuotaUpdateRequest,
    _: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
):
    if payload.world_entry_limit is None and payload.model_call_limit is None:
        raise HTTPException(status_code=400, detail="至少需要提供一个可更新的额度字段")
    _validate_limits(
        world_entry_limit=payload.world_entry_limit,
        model_call_limit=payload.model_call_limit,
    )

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    _apply_user_limits(
        user=user,
        world_entry_limit=payload.world_entry_limit,
        model_call_limit=payload.model_call_limit,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_admin_user_read(user)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
):
    if not payload.model_fields_set:
        raise HTTPException(status_code=400, detail="未提供可更新字段")

    _validate_limits(
        world_entry_limit=payload.world_entry_limit,
        model_call_limit=payload.model_call_limit,
    )

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if payload.is_admin is False and user.is_admin:
        if user.id == current_admin.id:
            raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
        if _admin_count(session) <= 1:
            raise HTTPException(status_code=400, detail="系统至少需要保留一个管理员")

    if "nickname" in payload.model_fields_set:
        user.nickname = payload.nickname or user.username
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin

    _apply_user_limits(
        user=user,
        world_entry_limit=payload.world_entry_limit,
        model_call_limit=payload.model_call_limit,
    )

    if payload.model_calls_used_today is not None:
        if payload.model_calls_used_today > user.daily_model_call_limit:
            raise HTTPException(status_code=400, detail="model_calls_used_today 不能超过模型调用上限")
        user.used_model_calls_today = payload.model_calls_used_today

    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_admin_user_read(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
    if user.is_admin and _admin_count(session) <= 1:
        raise HTTPException(status_code=400, detail="系统至少需要保留一个管理员")

    game_sessions = session.exec(select(GameSession).where(GameSession.user_id == user.id)).all()
    for game_session in game_sessions:
        session.delete(game_session)
    session.delete(user)
    session.commit()
    return {"message": "删除成功"}
