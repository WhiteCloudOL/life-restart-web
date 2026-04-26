from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_current_admin_user, get_session
from app.core.rate_limit import admin_rate_limiter
from app.models.user import User
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserQuotaUpdateRequest,
    AdminUserRead,
    AdminUserUpdateRequest,
    PaginatedUsersResponse,
)
from app.services.admin_service import AdminApplicationService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_service(session: AsyncSession = Depends(get_session)) -> AdminApplicationService:
    return AdminApplicationService(session)


@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    __: User = Depends(get_current_admin_user),
    _: None = admin_rate_limiter,
    service: AdminApplicationService = Depends(get_admin_service),
) -> PaginatedUsersResponse:
    return await service.list_users(page=page, size=size)


@router.post("/users", response_model=AdminUserRead, status_code=201)
async def create_user(
    payload: AdminUserCreateRequest,
    __: User = Depends(get_current_admin_user),
    _: None = admin_rate_limiter,
    service: AdminApplicationService = Depends(get_admin_service),
) -> AdminUserRead:
    return await service.create_user(payload)


@router.put("/users/{user_id}/quota", response_model=AdminUserRead)
async def update_user_quota(
    user_id: int,
    payload: AdminUserQuotaUpdateRequest,
    __: User = Depends(get_current_admin_user),
    _: None = admin_rate_limiter,
    service: AdminApplicationService = Depends(get_admin_service),
) -> AdminUserRead:
    return await service.update_user_quota(user_id, payload)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
async def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    current_admin: User = Depends(get_current_admin_user),
    _: None = admin_rate_limiter,
    service: AdminApplicationService = Depends(get_admin_service),
) -> AdminUserRead:
    return await service.update_user(user_id=user_id, payload=payload, current_admin=current_admin)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    _: None = admin_rate_limiter,
    service: AdminApplicationService = Depends(get_admin_service),
) -> dict[str, str]:
    return await service.delete_user(user_id=user_id, current_admin=current_admin)
