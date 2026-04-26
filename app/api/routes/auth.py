from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.app_config import get_app_config
from app.core.deps import get_session
from app.core.security import (
    create_access_token,
    has_usable_user_secret,
    hash_password,
    verify_password,
)
from app.models.user import User
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

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> UserRead:
    result = await session.exec(select(User).where(User.username == payload.username))
    existing_user = result.first()
    if existing_user:
        raise HTTPException(status_code=409, detail="用户名已存在")

    app_config = get_app_config()
    user = User(
        username=payload.username,
        nickname=payload.username,
        hashed_password=hash_password(payload.password),
        daily_quota=app_config.quota.default_daily_quota,
        daily_model_call_limit=app_config.quota.default_daily_model_call_limit,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserRead(
        id=user.id,
        username=user.username,
        nickname=(user.nickname or "").strip() or user.username,
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


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    # 登录失败统一提示，减少用户名枚举风险
    generic_error = HTTPException(status_code=401, detail="用户名或密码错误")
    enforce_ip_login_rate_limit(request)
    result = await session.exec(select(User).where(User.username == payload.username))
    user = result.first()
    if user:
        enforce_account_login_allowed(user)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    if not user:
        record_ip_login_failure(request)
        raise generic_error
    if not verify_password(payload.password, user.hashed_password):
        record_ip_login_failure(request)
        account_locked = record_account_login_failure(user)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        if account_locked:
            raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后重试")
        raise generic_error

    clear_ip_login_failures(request)
    clear_account_login_failures(user)
    session.add(user)
    await session.commit()
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
