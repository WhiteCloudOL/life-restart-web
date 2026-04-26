from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_current_user, get_session
from app.core.rate_limit import profile_rate_limiter
from app.models.user import User
from app.schemas.game import GameSessionRead
from app.schemas.user import UserRead, UserUpdateRequest
from app.services.user_service import UserApplicationService

router = APIRouter(prefix="/user", tags=["user"])


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserApplicationService:
    return UserApplicationService(session)


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
    _: None = profile_rate_limiter,
    service: UserApplicationService = Depends(get_user_service),
) -> UserRead:
    return await service.get_me(current_user)


@router.put("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    _: None = profile_rate_limiter,
    service: UserApplicationService = Depends(get_user_service),
) -> UserRead:
    return await service.update_me(payload, current_user)


@router.get("/history", response_model=list[GameSessionRead])
async def my_history(
    current_user: User = Depends(get_current_user),
    _: None = profile_rate_limiter,
    service: UserApplicationService = Depends(get_user_service),
) -> list[GameSessionRead]:
    return await service.get_history(current_user)
