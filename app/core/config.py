from functools import lru_cache
from typing import Annotated, List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.config_template_sync import ensure_runtime_configs_synced

class Settings(BaseSettings):
    APP_NAME: str = "AI Life Simulator Backend"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    DATA_DIR: str = "data"
    DATABASE_URL: str = "sqlite:///./data/life_simulator.db"
    APP_CONFIG_PATH: str = "config/app_config.toml"
    WORLD_CONFIG_PATH: str = "config/world_config.toml"

    # 生产环境务必通过环境变量覆盖，避免默认值泄露风险
    SECRET_KEY: str = "dev-only-change-this-secret-key-immediately"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    # 用于加密用户自定义 API Key 的密钥材料（不会直接用于 JWT）
    USER_DATA_ENCRYPTION_SECRET: str = "dev-only-change-this-encryption-secret-immediately"

    # 前端访问路径（开发态和生产态可不同）
    FRONTEND_DEV_ORIGIN: str = "http://127.0.0.1:5173"
    FRONTEND_PUBLIC_ORIGIN: str = ""
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = []

    # 传输安全与代理配置
    ENFORCE_HTTPS: bool = False
    TRUST_X_FORWARDED_PROTO: bool = True

    # python main.py 时是否同时拉起前端开发服务器
    START_FRONTEND_WITH_BACKEND: bool = True
    FRONTEND_DIR: str = "frontend"
    FRONTEND_DEV_COMMAND: str = "npm run dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [part.strip() for part in value.split(",") if part.strip()]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY 长度必须至少 32 个字符")
        return value

    @field_validator("USER_DATA_ENCRYPTION_SECRET")
    @classmethod
    def validate_encryption_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("USER_DATA_ENCRYPTION_SECRET 长度必须至少 32 个字符")
        return value

    @model_validator(mode="after")
    def finalize_origins(self):
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS if origin.strip()]
        if self.FRONTEND_DEV_ORIGIN.strip() and self.FRONTEND_DEV_ORIGIN not in origins:
            origins.append(self.FRONTEND_DEV_ORIGIN.strip())
        if self.FRONTEND_PUBLIC_ORIGIN.strip() and self.FRONTEND_PUBLIC_ORIGIN not in origins:
            origins.append(self.FRONTEND_PUBLIC_ORIGIN.strip())
        self.ALLOWED_ORIGINS = origins
        return self


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    ensure_runtime_configs_synced(
        app_config_path=settings.APP_CONFIG_PATH,
        world_config_path=settings.WORLD_CONFIG_PATH,
    )
    return settings
