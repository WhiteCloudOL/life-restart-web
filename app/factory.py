from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router
from app.core.app_config import get_app_config_provider
from app.core.config import Settings, get_settings
from app.core.middleware import setup_middlewares
from app.core.world_config import get_world_config_provider
from app.db.init_db import init_db, migrate_user_secret_storage, seed_default_admin, seed_default_presets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用启动阶段只做基础设施预热，不在这里放业务逻辑。"""

    # 先预热 TOML 配置缓存，避免首次请求时再触发磁盘读取。
    get_app_config_provider().reload()
    get_world_config_provider().reload()

    await init_db()
    await seed_default_presets()
    await seed_default_admin()
    await migrate_user_secret_storage()
    yield


def _mount_frontend_dist(app: FastAPI, settings: Settings) -> None:
    """仅在非开发环境挂载前端构建产物。

    开发环境仍由 Vite Dev Server 提供页面，避免后端强耦合前端热更新。
    """

    if not settings.should_mount_frontend_dist:
        return

    app.mount(
        "/",
        StaticFiles(directory=settings.FRONTEND_DIST_DIR, html=True),
        name="frontend",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
    setup_middlewares(application)
    application.include_router(api_router, prefix=settings.API_PREFIX)

    @application.get("/healthz", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"message": "AI Life Simulator backend is running"}

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(_: FastAPI, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})

    _mount_frontend_dist(application, settings)
    return application
