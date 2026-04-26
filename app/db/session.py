from __future__ import annotations

from collections.abc import AsyncIterator
from importlib.util import find_spec
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import Settings, get_settings


def _ensure_sqlite_data_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    db_path_raw = database_url.replace("sqlite:///", "", 1)
    db_path = Path(db_path_raw)
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _build_async_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return database_url


def _build_sync_connect_args(settings: Settings) -> dict[str, bool | float]:
    if settings.DATABASE_URL.startswith("sqlite"):
        return {"check_same_thread": False, "timeout": 30.0}
    return {}


def _build_async_connect_args(settings: Settings) -> dict[str, bool | float]:
    if settings.DATABASE_URL.startswith("sqlite"):
        return {"check_same_thread": False, "timeout": 30.0}
    return {}


def _configure_sqlite_connection(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
    finally:
        cursor.close()


settings = get_settings()
_ensure_sqlite_data_dir(settings.DATABASE_URL)
ASYNC_SQLITE_DRIVER_AVAILABLE = find_spec("aiosqlite") is not None

# 保留同步引擎作为过渡兼容层，供尚未迁移的基础工具与脚本使用。
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_build_sync_connect_args(settings),
    echo=False,
)

if settings.DATABASE_URL.startswith("sqlite"):
    event.listen(engine, "connect", _configure_sqlite_connection)

async_engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None

if ASYNC_SQLITE_DRIVER_AVAILABLE:
    async_engine = create_async_engine(
        _build_async_database_url(settings.DATABASE_URL),
        connect_args=_build_async_connect_args(settings),
        echo=False,
        future=True,
    )
    if settings.DATABASE_URL.startswith("sqlite"):
        event.listen(async_engine.sync_engine, "connect", _configure_sqlite_connection)
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_async_session() -> AsyncIterator[AsyncSession]:
    if async_session_factory is None:
        raise RuntimeError("异步数据库会话不可用：缺少 aiosqlite 依赖")
    async with async_session_factory() as session:
        yield session


def get_sync_session() -> Session:
    return Session(engine)
