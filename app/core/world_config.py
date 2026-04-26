from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings


class StartupAttributeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=50)
    purpose: str = Field(default="属性作用待配置", min_length=1, max_length=200)
    min_value: int = Field(default=0, ge=0, le=1000)
    max_value: int = Field(default=100, ge=0, le=1000)
    default_value: int = Field(default=0, ge=0, le=1000)


class StartupPresetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1000)
    worldview: str = Field(min_length=1, max_length=2000)
    character_options: list[str] = Field(default_factory=list, max_length=20)
    attributes: list[StartupAttributeConfig] = Field(min_length=1, max_length=20)
    max_attribute_points: int = Field(default=200, ge=1, le=10000)
    start_age: int = Field(default=18, ge=0, le=200)
    age_step: int = Field(default=1, ge=0, le=20)
    is_custom: bool = False


class CustomPresetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    id: int = Field(default=9999, gt=0)
    title: str = Field(default="自定义预设", min_length=1, max_length=128)
    description: str = Field(default="自由输入世界观与角色设定，开始专属人生线路。", min_length=1, max_length=1000)
    default_worldview: str = Field(default="", max_length=2000)
    max_attribute_points: int = Field(default=15, ge=1, le=10000)
    start_age: int = Field(default=18, ge=0, le=200)
    age_step: int = Field(default=1, ge=0, le=20)
    attributes: list[StartupAttributeConfig] = Field(min_length=1, max_length=20)


class WorldConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startup_presets: list[StartupPresetConfig] = Field(min_length=1, max_length=50)
    custom_preset: CustomPresetConfig | None = None


def load_world_config(path: Path) -> WorldConfig:
    if not path.exists():
        raise RuntimeError(f"世界配置文件不存在: {path}")
    with path.open("rb") as file:
        raw = tomllib.load(file)
    return WorldConfig.model_validate(raw)


class WorldConfigProvider:
    """世界配置提供器，统一管理缓存与重载。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cached_config: WorldConfig | None = None

    def get(self) -> WorldConfig:
        if self._cached_config is None:
            self._cached_config = load_world_config(self._settings.WORLD_CONFIG_PATH)
        return self._cached_config

    def reload(self) -> WorldConfig:
        self._cached_config = load_world_config(self._settings.WORLD_CONFIG_PATH)
        return self._cached_config


@lru_cache
def get_world_config_provider() -> WorldConfigProvider:
    return WorldConfigProvider(get_settings())


def get_world_config() -> WorldConfig:
    return get_world_config_provider().get()
