from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.game import (
    GameForceExitRequest,
    GameForceExitResponse,
    GameNextRequest,
    GameStartRequest,
    GameStepResponse,
    PresetRead,
)
from app.services.game_service import GameApplicationService

router = APIRouter(prefix="/game", tags=["game"])


def get_game_service(session: AsyncSession = Depends(get_session)) -> GameApplicationService:
    return GameApplicationService(session)


@router.get("/presets", response_model=list[PresetRead])
async def list_presets(
    _: User = Depends(get_current_user),
    service: GameApplicationService = Depends(get_game_service),
) -> list[PresetRead]:
    return await service.list_presets()


@router.post("/start", response_model=GameStepResponse)
async def game_start(
    payload: GameStartRequest,
    current_user: User = Depends(get_current_user),
    service: GameApplicationService = Depends(get_game_service),
) -> GameStepResponse:
    return await service.start_game(payload, current_user)


@router.post("/next", response_model=GameStepResponse)
async def game_next(
    payload: GameNextRequest,
    current_user: User = Depends(get_current_user),
    service: GameApplicationService = Depends(get_game_service),
) -> GameStepResponse:
    return await service.advance_game(payload, current_user)


@router.post("/force-exit", response_model=GameForceExitResponse)
async def force_exit_game(
    payload: GameForceExitRequest,
    current_user: User = Depends(get_current_user),
    service: GameApplicationService = Depends(get_game_service),
) -> GameForceExitResponse:
    return await service.force_exit_game(payload, current_user)
