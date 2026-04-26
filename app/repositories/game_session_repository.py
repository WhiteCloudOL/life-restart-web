from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.game_session import GameSession


class GameSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_owned_session(self, *, session_id: int, user_id: int) -> GameSession | None:
        result = await self.session.exec(
            select(GameSession).where(
                GameSession.id == session_id,
                GameSession.user_id == user_id,
            )
        )
        return result.first()

    async def list_user_history(self, *, user_id: int, limit: int) -> list[GameSession]:
        result = await self.session.exec(
            select(GameSession)
            .where(GameSession.user_id == user_id)
            .order_by(GameSession.id.desc())
            .limit(limit)
        )
        return result.all()

    async def list_by_user_id(self, user_id: int) -> list[GameSession]:
        result = await self.session.exec(select(GameSession).where(GameSession.user_id == user_id))
        return result.all()

    async def save(self, game_session: GameSession) -> GameSession:
        self.session.add(game_session)
        await self.session.commit()
        await self.session.refresh(game_session)
        return game_session
