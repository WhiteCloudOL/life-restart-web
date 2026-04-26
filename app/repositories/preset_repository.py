from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.preset import Preset


class PresetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, preset_id: int) -> Preset | None:
        result = await self.session.exec(select(Preset).where(Preset.id == preset_id))
        return result.first()

    async def save(self, preset: Preset) -> Preset:
        self.session.add(preset)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset
