from datetime import date
from typing import Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class UserRead(BaseModel):
    id: int
    username: str
    nickname: str
    api_mode: Literal["default", "custom"]
    has_custom_api_key: bool
    custom_model_name: Optional[str]
    custom_base_url: Optional[str]
    is_admin: bool
    world_entry_limit: int
    world_entries_used_today: int
    model_call_limit: int
    model_calls_used_today: int
    last_active_date: date

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: Optional[str] = Field(default=None, max_length=32)
    api_mode: Optional[Literal["default", "custom"]] = None
    custom_api_key: Optional[str] = Field(default=None, max_length=2048)
    custom_model_name: Optional[str] = Field(default=None, max_length=200)
    custom_base_url: Optional[AnyHttpUrl] = None

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip()

    @field_validator("custom_api_key", "custom_model_name")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None
