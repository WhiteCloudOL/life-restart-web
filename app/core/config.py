from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.config_template_sync import ensure_runtime_configs_synced


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """应用运行时设置。

    这一层只负责环境变量与路径归一化，不负责业务配置文件内容解析。
    """

    APP_NAME: str = "AI Life Simulator Backend"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    PROJECT_ROOT: Path = _project_root()
    DATA_DIR: Path = Path("data")
    DATABASE_URL: str = "sqlite:///./data/life_simulator.db"
    APP_CONFIG_PATH: Path = Path("config/app_config.toml")
    WORLD_CONFIG_PATH: Path = Path("config/world_config.toml")

    # 生产环境必须使用环境变量覆盖，禁止依赖默认密钥。
    SECRET_KEY: str = "dev-only-change-this-secret-key-immediately"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    USER_DATA_ENCRYPTION_SECRET: str = "dev-only-change-this-encryption-secret-immediately"
    DEFAULT_ADMIN_PASSWORD: str = ""

    # 前端访问配置
    FRONTEND_DEV_ORIGIN: str = "http://127.0.0.1:5173"
    FRONTEND_PUBLIC_ORIGIN: str = ""
    FRONTEND_DIST_DIR: Path = Path("frontend/dist")
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = []

    # 代理与 HTTPS 配置
    ENFORCE_HTTPS: bool = False
    TRUST_X_FORWARDED_PROTO: bool = True
    TRUST_X_FORWARDED_FOR: bool = False

    # 登录安全防护
    LOGIN_MAX_FAILURES_PER_ACCOUNT: int = 5
    LOGIN_ACCOUNT_LOCK_MINUTES: int = 15
    LOGIN_MAX_ATTEMPTS_PER_IP_WINDOW: int = 20
    LOGIN_IP_WINDOW_SECONDS: int = 300

    # 开发辅助：仅 `python main.py` 这一类本地联调场景使用。
    START_FRONTEND_WITH_BACKEND: bool = True
    FRONTEND_DIR: Path = Path("frontend")
    FRONTEND_DEV_COMMAND: str = "npm run dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"development", "testing", "staging", "production"}
        if normalized not in allowed:
            raise ValueError(f"ENVIRONMENT 必须是 {sorted(allowed)} 之一")
        return normalized

    @field_validator("API_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("API_PREFIX 必须以 / 开头")
        if cleaned != "/" and cleaned.endswith("/"):
            cleaned = cleaned.rstrip("/")
        return cleaned

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [item.strip() for item in value if item.strip()]
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

    @field_validator("DEFAULT_ADMIN_PASSWORD")
    @classmethod
    def strip_optional_secrets(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def normalize_paths(self) -> Settings:
        base_dir = self.PROJECT_ROOT
        self.DATA_DIR = self._resolve_path(self.DATA_DIR, base_dir)
        self.APP_CONFIG_PATH = self._resolve_path(self.APP_CONFIG_PATH, base_dir)
        self.WORLD_CONFIG_PATH = self._resolve_path(self.WORLD_CONFIG_PATH, base_dir)
        self.FRONTEND_DIR = self._resolve_path(self.FRONTEND_DIR, base_dir)
        self.FRONTEND_DIST_DIR = self._resolve_path(self.FRONTEND_DIST_DIR, base_dir)
        return self

    @model_validator(mode="after")
    def finalize_origins(self) -> Settings:
        merged_origins: list[str] = []
        for origin in self.ALLOWED_ORIGINS:
            if origin not in merged_origins:
                merged_origins.append(origin)
        for candidate in (self.FRONTEND_DEV_ORIGIN.strip(), self.FRONTEND_PUBLIC_ORIGIN.strip()):
            if candidate and candidate not in merged_origins:
                merged_origins.append(candidate)
        self.ALLOWED_ORIGINS = merged_origins
        return self

    @model_validator(mode="after")
    def validate_security_guards(self) -> Settings:
        if self.ENVIRONMENT == "production":
            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("生产环境禁止在 ALLOWED_ORIGINS 中使用通配符 *")
            if self.FRONTEND_PUBLIC_ORIGIN.strip() == "":
                raise ValueError("生产环境必须配置 FRONTEND_PUBLIC_ORIGIN")
            if self.SECRET_KEY.startswith("dev-only-change-this-"):
                raise ValueError("生产环境必须显式配置 SECRET_KEY")
            if self.USER_DATA_ENCRYPTION_SECRET.startswith("dev-only-change-this-"):
                raise ValueError("生产环境必须显式配置 USER_DATA_ENCRYPTION_SECRET")
        if self.LOGIN_MAX_FAILURES_PER_ACCOUNT < 1:
            raise ValueError("LOGIN_MAX_FAILURES_PER_ACCOUNT 必须至少为 1")
        if self.LOGIN_ACCOUNT_LOCK_MINUTES < 1:
            raise ValueError("LOGIN_ACCOUNT_LOCK_MINUTES 必须至少为 1")
        if self.LOGIN_MAX_ATTEMPTS_PER_IP_WINDOW < 1:
            raise ValueError("LOGIN_MAX_ATTEMPTS_PER_IP_WINDOW 必须至少为 1")
        if self.LOGIN_IP_WINDOW_SECONDS < 1:
            raise ValueError("LOGIN_IP_WINDOW_SECONDS 必须至少为 1")
        return self

    @staticmethod
    def _resolve_path(path_value: Path, base_dir: Path) -> Path:
        if path_value.is_absolute():
            return path_value
        return (base_dir / path_value).resolve()

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def should_mount_frontend_dist(self) -> bool:
        return self.FRONTEND_DIST_DIR.exists() and not self.is_development


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    ensure_runtime_configs_synced(
        app_config_path=str(settings.APP_CONFIG_PATH),
        world_config_path=str(settings.WORLD_CONFIG_PATH),
    )
    return settings
