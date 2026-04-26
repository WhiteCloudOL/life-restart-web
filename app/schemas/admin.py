from datetime import date
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.security import validate_password_strength, validate_username


class AdminUserRead(BaseModel):
    id: int
    username: str
    nickname: str
    api_mode: str
    is_admin: bool
    world_entry_limit: int
    world_entries_used_today: int
    model_call_limit: int
    model_calls_used_today: int
    last_active_date: date
    has_custom_api_key: bool

    model_config = ConfigDict(extra="forbid")


class AdminUserQuotaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    world_entry_limit: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("world_entry_limit", "daily_quota"),
    )
    model_call_limit: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("model_call_limit", "daily_model_call_limit"),
    )


class AdminUserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=128)
    nickname: Optional[str] = Field(default=None, max_length=32)
    is_admin: bool = False

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return validate_username(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if len(trimmed) > 32:
            raise ValueError("昵称长度不能超过 32 个字符")
        return trimmed or None


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: Optional[str] = Field(default=None, max_length=32)
    password: Optional[str] = Field(default=None, min_length=10, max_length=128)
    is_admin: Optional[bool] = None
    world_entry_limit: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("world_entry_limit", "daily_quota"),
    )
    model_call_limit: Optional[int] = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("model_call_limit", "daily_model_call_limit"),
    )
    model_calls_used_today: Optional[int] = Field(default=None, ge=0)

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if len(trimmed) > 32:
            raise ValueError("昵称长度不能超过 32 个字符")
        return trimmed or None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        validate_password_strength(value)
        return value


class PaginatedUsersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int
    size: int
    total: int
    items: list[AdminUserRead]
    next_page: Optional[int]
