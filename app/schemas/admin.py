from datetime import date
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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


class PaginatedUsersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int
    size: int
    total: int
    items: list[AdminUserRead]
    next_page: Optional[int]
