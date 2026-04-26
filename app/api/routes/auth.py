from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_session
from app.core.rate_limit import auth_rate_limiter
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthApplicationService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthApplicationService:
    return AuthApplicationService(session)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    _: None = auth_rate_limiter,
    service: AuthApplicationService = Depends(get_auth_service),
) -> UserRead:
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    _: None = auth_rate_limiter,
    service: AuthApplicationService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.login(payload, request)
