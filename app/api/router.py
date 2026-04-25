from fastapi import APIRouter

from app.api.routes import admin, auth, game, user

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(admin.router)
api_router.include_router(game.router)

