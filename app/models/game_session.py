from typing import Optional

from sqlmodel import Field, SQLModel


class GameSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    preset_id: int = Field(foreign_key="preset.id", index=True, nullable=False)
    current_stats: str = Field(nullable=False)  # JSON 字符串
    event_history: str = Field(nullable=False)  # JSON 字符串（数组）
    is_ended: bool = Field(default=False, nullable=False)

