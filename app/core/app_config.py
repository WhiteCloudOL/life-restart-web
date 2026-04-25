import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core.config import get_settings


class DefaultModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "openai_compatible"
    model: str = Field(min_length=1, max_length=200)
    base_url: HttpUrl
    # 系统默认模型 API Key（仅服务端使用，不通过接口返回）
    api_key: str = Field(default="", max_length=500)


class QuotaConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_daily_quota: int = Field(ge=0, le=100000)
    max_daily_quota: int = Field(ge=0, le=100000)
    default_daily_model_call_limit: int = Field(ge=0, le=100000)
    max_daily_model_call_limit: int = Field(ge=0, le=100000)


class FrontendConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # 前端公共访问入口（用于文档与外部系统集成）
    public_origin: str = "http://127.0.0.1:5173"
    # 前端路由基路径（网关有子路径部署时可调整）
    route_base: str = "/"


class GameplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_attribute_points: int = Field(default=15, ge=1, le=10000)
    death_stat_keys: list[str] = Field(
        default_factory=lambda: ["health", "体质", "生命", "生存", "hp"],
        min_length=1,
        max_length=20,
    )
    death_stat_threshold: int = Field(default=0, ge=-10000, le=10000)
    death_event_keywords: list[str] = Field(
        default_factory=lambda: ["死亡", "去世", "身亡", "当场死亡", "终年", "dead", "died"],
        min_length=1,
        max_length=50,
    )
    default_next_choices: list[str] = Field(
        default_factory=lambda: [
            "[高风险] 孤注一掷投入高杠杆计划：若成功可迅速获得巨额资源与关键人脉，但失败将触发致命级连锁危机，可能直接结束人生。",
            "[中风险] 与关键势力进行策略博弈：有机会稳步提升地位并拿到阶段性收益，但判断失误会遭遇重创，存在较高失败概率。",
            "[低风险] 选择保守积累与基础建设：收益较慢但稳定，长期有助于提升生存韧性；仅在连续误判或外部突发事件下才可能走向终局。",
        ],
        min_length=3,
        max_length=3,
    )
    max_next_choices: int = Field(default=3, ge=3, le=3)


class DefaultAdminConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(default="admin", min_length=1, max_length=32)
    password: str = Field(default="Admin@12345678", min_length=1, max_length=128)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_model: DefaultModelConfig
    default_admin: DefaultAdminConfig = Field(default_factory=DefaultAdminConfig)
    quota: QuotaConfig
    frontend: FrontendConfig = Field(default_factory=FrontendConfig)
    gameplay: GameplayConfig = Field(default_factory=GameplayConfig)


def load_app_config(path: str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise RuntimeError(f"配置文件不存在: {path}")
    with config_path.open("rb") as f:
        raw = tomllib.load(f)
    return AppConfig.model_validate(raw)


@lru_cache
def get_app_config() -> AppConfig:
    settings = get_settings()
    return load_app_config(settings.APP_CONFIG_PATH)
