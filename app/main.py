from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.middleware import setup_middlewares
from app.db.init_db import init_db, migrate_user_secret_storage, seed_default_admin, seed_default_presets


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动阶段初始化数据库结构并注入默认预设数据
    init_db()
    seed_default_presets()
    seed_default_admin()
    migrate_user_secret_storage()
    yield


settings = get_settings()
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
setup_middlewares(app)
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
def health_check():
    return {"message": "AI Life Simulator backend is running"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    # 统一兜底，避免把内部错误栈直接暴露给客户端
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
