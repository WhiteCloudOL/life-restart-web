from __future__ import annotations

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.app_config import get_app_config
from app.core.security import hash_password
from app.models.user import User
from app.repositories.game_session_repository import GameSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserQuotaUpdateRequest,
    AdminUserRead,
    AdminUserUpdateRequest,
    PaginatedUsersResponse,
)
from app.services.user_view import to_admin_user_read


class AdminApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.game_session_repository = GameSessionRepository(session)

    async def list_users(self, *, page: int, size: int) -> PaginatedUsersResponse:
        total = await self.user_repository.count_all()
        offset = (page - 1) * size
        users = await self.user_repository.list_paginated(offset=offset, limit=size)
        items = [to_admin_user_read(user) for user in users]
        next_page = page + 1 if offset + size < total else None
        return PaginatedUsersResponse(page=page, size=size, total=total, items=items, next_page=next_page)

    async def create_user(self, payload: AdminUserCreateRequest) -> AdminUserRead:
        existing_user = await self.user_repository.get_by_username(payload.username)
        if existing_user is not None:
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
        saved_user = await self.user_repository.save(user)
        return to_admin_user_read(saved_user)

    async def update_user_quota(self, user_id: int, payload: AdminUserQuotaUpdateRequest) -> AdminUserRead:
        if payload.world_entry_limit is None and payload.model_call_limit is None:
            raise HTTPException(status_code=400, detail="至少需要提供一个可更新的额度字段")
        self._validate_limits(
            world_entry_limit=payload.world_entry_limit,
            model_call_limit=payload.model_call_limit,
        )

        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        self._apply_user_limits(
            user=user,
            world_entry_limit=payload.world_entry_limit,
            model_call_limit=payload.model_call_limit,
        )
        saved_user = await self.user_repository.save(user)
        return to_admin_user_read(saved_user)

    async def update_user(
        self,
        *,
        user_id: int,
        payload: AdminUserUpdateRequest,
        current_admin: User,
    ) -> AdminUserRead:
        if not payload.model_fields_set:
            raise HTTPException(status_code=400, detail="未提供可更新字段")
        self._validate_limits(
            world_entry_limit=payload.world_entry_limit,
            model_call_limit=payload.model_call_limit,
        )

        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        if payload.is_admin is False and user.is_admin:
            if self._require_user_id(user) == self._require_user_id(current_admin):
                raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
            if await self.user_repository.count_admins() <= 1:
                raise HTTPException(status_code=400, detail="系统至少需要保留一个管理员")

        if "nickname" in payload.model_fields_set:
            user.nickname = payload.nickname or user.username
        if payload.password is not None:
            user.hashed_password = hash_password(payload.password)
        if payload.is_admin is not None:
            user.is_admin = payload.is_admin

        self._apply_user_limits(
            user=user,
            world_entry_limit=payload.world_entry_limit,
            model_call_limit=payload.model_call_limit,
        )
        if payload.model_calls_used_today is not None:
            if payload.model_calls_used_today > user.daily_model_call_limit:
                raise HTTPException(status_code=400, detail="model_calls_used_today 不能超过模型调用上限")
            user.used_model_calls_today = payload.model_calls_used_today

        saved_user = await self.user_repository.save(user)
        return to_admin_user_read(saved_user)

    async def delete_user(self, *, user_id: int, current_admin: User) -> dict[str, str]:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        if self._require_user_id(user) == self._require_user_id(current_admin):
            raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
        if user.is_admin and await self.user_repository.count_admins() <= 1:
            raise HTTPException(status_code=400, detail="系统至少需要保留一个管理员")

        game_sessions = await self.game_session_repository.list_by_user_id(self._require_user_id(user))
        for game_session in game_sessions:
            await self.session.delete(game_session)
        await self.session.delete(user)
        await self.session.commit()
        return {"message": "删除成功"}

    @staticmethod
    def _validate_limits(*, world_entry_limit: int | None, model_call_limit: int | None) -> None:
        app_config = get_app_config()
        if world_entry_limit is not None and world_entry_limit > app_config.quota.max_daily_quota:
            raise HTTPException(status_code=400, detail="world_entry_limit 超出系统允许上限")
        if model_call_limit is not None and model_call_limit > app_config.quota.max_daily_model_call_limit:
            raise HTTPException(status_code=400, detail="model_call_limit 超出系统允许上限")

    @staticmethod
    def _apply_user_limits(*, user: User, world_entry_limit: int | None, model_call_limit: int | None) -> None:
        if world_entry_limit is not None:
            user.daily_quota = world_entry_limit
            if user.used_quota_today > user.daily_quota:
                user.used_quota_today = user.daily_quota
        if model_call_limit is not None:
            user.daily_model_call_limit = model_call_limit
            if user.used_model_calls_today > user.daily_model_call_limit:
                user.used_model_calls_today = user.daily_model_call_limit

    @staticmethod
    def _require_user_id(user: User) -> int:
        if user.id is None:
            raise HTTPException(status_code=500, detail="用户状态异常，缺少用户标识")
        return user.id
