from pathlib import Path

from sqlmodel import create_engine

from app.core.config import get_settings

settings = get_settings()


def ensure_sqlite_data_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path_raw = database_url.replace("sqlite:///", "", 1)
    db_path = Path(db_path_raw)
    # sqlite:///./data/xxx.db => 自动创建 data 目录
    db_path.parent.mkdir(parents=True, exist_ok=True)


ensure_sqlite_data_dir(settings.DATABASE_URL)
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=False)
