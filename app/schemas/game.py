from pydantic import BaseModel, ConfigDict, Field


class GameStartRequest(BaseModel):
    preset_id: int = Field(gt=0)
    selected_character_setting: str | None = Field(default=None, max_length=80)
    custom_worldview: str | None = Field(default=None, max_length=2000)
    custom_character_setting: str | None = Field(default=None, max_length=500)
    allocated_attributes: dict[str, int] = Field(default_factory=dict)
    custom_prompt: str | None = Field(default=None, max_length=200)


class GameNextRequest(BaseModel):
    session_id: int = Field(gt=0)
    user_choice: str = Field(min_length=1, max_length=500)


class GameSessionRead(BaseModel):
    id: int
    user_id: int
    preset_id: int
    current_stats: dict[str, object]
    event_history: list[dict[str, object]]
    is_ended: bool

    model_config = ConfigDict(extra="forbid")


class PresetRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    title: str
    description: str
    worldview: str
    character_options: list[str]
    max_attribute_points: int
    is_custom: bool = False
    attributes: list[dict[str, object]]


class GameStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: int
    event: str
    event_segments: list[str]
    current_stats: dict[str, object]
    is_ended: bool
    world_entry_limit: int
    world_entries_used_today: int
    model_call_limit: int
    model_calls_used_today: int
    next_choices: list[str]
    end_reason: str | None = None
    end_summary: str | None = None


class GameForceExitRequest(BaseModel):
    session_id: int = Field(gt=0)


class GameForceExitResponse(BaseModel):
    success: bool
    end_reason: str | None = None
    end_summary: str | None = None
