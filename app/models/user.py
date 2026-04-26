from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(
        sa_column=Column("username", String(32), unique=True, index=True, nullable=False)
    )
    nickname: Optional[str] = Field(default=None, sa_column=Column(String(32), nullable=True))
    hashed_password: str = Field(nullable=False)
    api_mode: str = Field(default="default", sa_column=Column(String(16), nullable=False))
    custom_api_key: Optional[str] = Field(default=None, nullable=True)
    custom_model_name: Optional[str] = Field(default=None, sa_column=Column(String(200), nullable=True))
    custom_base_url: Optional[str] = Field(default=None, sa_column=Column(String(500), nullable=True))
    is_admin: bool = Field(default=False, nullable=False)
    daily_quota: int = Field(default=20, ge=0, nullable=False)
    used_quota_today: int = Field(default=0, ge=0, nullable=False)
    daily_model_call_limit: int = Field(default=80, ge=0, nullable=False)
    used_model_calls_today: int = Field(default=0, ge=0, nullable=False)
    last_active_date: date = Field(default_factory=date.today, nullable=False)
    failed_login_attempts: int = Field(default=0, ge=0, nullable=False)
    login_locked_until: Optional[datetime] = Field(default=None, nullable=True)
