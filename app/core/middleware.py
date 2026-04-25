from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store"
        # API 场景下默认禁止加载任意外部资源
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class HttpsEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.ENFORCE_HTTPS:
            return await call_next(request)

        scheme = request.url.scheme
        if settings.TRUST_X_FORWARDED_PROTO:
            forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
            if forwarded_proto:
                scheme = forwarded_proto

        if scheme != "https":
            return JSONResponse(status_code=400, content={"detail": "必须使用 HTTPS 访问"})
        return await call_next(request)


def setup_middlewares(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(HttpsEnforcementMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
