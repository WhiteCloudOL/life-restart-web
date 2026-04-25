from typing import Optional

from sqlmodel import Field, SQLModel


class Preset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=128)
    description: str = Field(nullable=False, max_length=1000)
    initial_stats: str = Field(nullable=False)  # JSON 字符串

