from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.app_config import get_app_config
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.login_guard import (
    clear_account_login_failures,
    clear_ip_login_failures,
    enforce_account_login_allowed,
    enforce_ip_login_rate_limit,
    record_account_login_failure,
    record_ip_login_failure,
)
from app.services.user_view import to_user_read


class AuthApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> UserRead:
        existing_user = await self.user_repository.get_by_username(payload.username)
        if existing_user is not None:
            raise HTTPException(status_code=409, detail="用户名已存在")

        app_config = get_app_config()
        user = User(
            username=payload.username,
            nickname=payload.username,
            hashed_password=hash_password(payload.password),
            daily_quota=app_config.quota.default_daily_quota,
            daily_model_call_limit=app_config.quota.default_daily_model_call_limit,
        )
        saved_user = await self.user_repository.save(user)
        return to_user_read(saved_user)

    async def login(self, payload: LoginRequest, request: Request) -> TokenResponse:
        generic_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        enforce_ip_login_rate_limit(request)
        user = await self.user_repository.get_by_username(payload.username)
        if user is not None:
            enforce_account_login_allowed(user)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

        if user is None:
            record_ip_login_failure(request)
            raise generic_error

        if not verify_password(payload.password, user.hashed_password):
            record_ip_login_failure(request)
            account_locked = record_account_login_failure(user)
            await self.user_repository.save(user)
            if account_locked:
                raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后重试")
            raise generic_error

        clear_ip_login_failures(request)
        clear_account_login_failures(user)
        await self.user_repository.save(user)
        token = create_access_token(str(self._require_user_id(user)))
        return TokenResponse(access_token=token)

    @staticmethod
    def _require_user_id(user: User) -> int:
        if user.id is None:
            raise HTTPException(status_code=500, detail="用户状态异常，缺少用户标识")
        return user.id
