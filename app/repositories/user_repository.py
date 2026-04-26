from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.exec(select(User).where(User.id == user_id))
        return result.first()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.exec(select(User).where(User.username == username))
        return result.first()

    async def list_paginated(self, *, offset: int, limit: int) -> list[User]:
        result = await self.session.exec(select(User).offset(offset).limit(limit))
        return result.all()

    async def count_all(self) -> int:
        result = await self.session.exec(select(User))
        return len(result.all())

    async def count_admins(self) -> int:
        result = await self.session.exec(select(User).where(User.is_admin == True))
        return len(result.all())

    async def save(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()
