from __future__ import annotations

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import encrypt_user_secret, has_usable_user_secret
from app.models.user import User
from app.repositories.game_session_repository import GameSessionRepository
from app.schemas.game import GameSessionRead
from app.schemas.user import UserRead, UserUpdateRequest
from app.services.game_engine import parse_json_array, parse_json_object
from app.services.quota import reset_quota_if_new_day
from app.services.user_view import to_user_read

MAX_HISTORY_RECORDS = 200


class UserApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.game_session_repository = GameSessionRepository(session)

    async def get_me(self, current_user: User) -> UserRead:
        reset_quota_if_new_day(current_user)
        self.session.add(current_user)
        await self.session.commit()
        await self.session.refresh(current_user)
        return to_user_read(current_user)

    async def update_me(self, payload: UserUpdateRequest, current_user: User) -> UserRead:
        if "nickname" in payload.model_fields_set:
            current_user.nickname = payload.nickname or current_user.username
        if "api_mode" in payload.model_fields_set and payload.api_mode is not None:
            current_user.api_mode = payload.api_mode
        if "custom_api_key" in payload.model_fields_set:
            current_user.custom_api_key = encrypt_user_secret(payload.custom_api_key) if payload.custom_api_key else None
        if "custom_model_name" in payload.model_fields_set:
            current_user.custom_model_name = payload.custom_model_name
        if "custom_base_url" in payload.model_fields_set:
            current_user.custom_base_url = str(payload.custom_base_url) if payload.custom_base_url else None

        if current_user.api_mode == "custom":
            if not (current_user.custom_model_name or "").strip():
                raise HTTPException(status_code=400, detail="启用自定义 API 模式前请先填写自定义模型名")
            if not has_usable_user_secret(current_user.custom_api_key):
                raise HTTPException(status_code=400, detail="启用自定义 API 模式前请先填写自定义 API Key")

        self.session.add(current_user)
        await self.session.commit()
        await self.session.refresh(current_user)
        return to_user_read(current_user)

    async def get_history(self, current_user: User) -> list[GameSessionRead]:
        user_id = self._require_user_id(current_user)
        sessions = await self.game_session_repository.list_user_history(user_id=user_id, limit=MAX_HISTORY_RECORDS)
        return [
            GameSessionRead(
                id=self._require_game_session_id(row.id),
                user_id=row.user_id,
                preset_id=row.preset_id,
                current_stats=parse_json_object(row.current_stats),
                event_history=parse_json_array(row.event_history),
                is_ended=row.is_ended,
            )
            for row in sessions
        ]

    @staticmethod
    def _require_user_id(user: User) -> int:
        if user.id is None:
            raise HTTPException(status_code=500, detail="用户状态异常，缺少用户标识")
        return user.id

    @staticmethod
    def _require_game_session_id(session_id: int | None) -> int:
        if session_id is None:
            raise HTTPException(status_code=500, detail="会话状态异常，缺少会话标识")
        return session_id
