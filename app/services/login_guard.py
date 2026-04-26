from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import get_settings
from app.models.user import User

_ip_attempts: dict[str, deque[datetime]] = defaultdict(deque)
_ip_attempts_lock = Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_request_ip(request: Request) -> str:
    settings = get_settings()
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded_for:
            return forwarded_for
    client = request.client
    return client.host if client and client.host else "unknown"


def enforce_ip_login_rate_limit(request: Request) -> None:
    settings = get_settings()
    current_time = utc_now()
    window_start = current_time - timedelta(seconds=settings.LOGIN_IP_WINDOW_SECONDS)
    request_ip = get_request_ip(request)
    with _ip_attempts_lock:
        attempts = _ip_attempts[request_ip]
        while attempts and attempts[0] <= window_start:
            attempts.popleft()
        if len(attempts) >= settings.LOGIN_MAX_ATTEMPTS_PER_IP_WINDOW:
            retry_after = max(1, int((attempts[0] - window_start).total_seconds()))
            raise HTTPException(
                status_code=429,
                detail="登录尝试过于频繁，请稍后重试",
                headers={"Retry-After": str(retry_after)},
            )


def record_ip_login_failure(request: Request) -> None:
    request_ip = get_request_ip(request)
    with _ip_attempts_lock:
        _ip_attempts[request_ip].append(utc_now())


def clear_ip_login_failures(request: Request) -> None:
    request_ip = get_request_ip(request)
    with _ip_attempts_lock:
        _ip_attempts.pop(request_ip, None)


def clear_expired_account_lock(user: User) -> bool:
    locked_until = user.login_locked_until
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until > utc_now():
        return False
    user.login_locked_until = None
    user.failed_login_attempts = 0
    return True


def enforce_account_login_allowed(user: User) -> None:
    clear_expired_account_lock(user)
    locked_until = user.login_locked_until
    if locked_until is None:
        return
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    retry_after = max(1, int((locked_until - utc_now()).total_seconds()))
    raise HTTPException(
        status_code=429,
        detail="登录尝试过于频繁，请稍后重试",
        headers={"Retry-After": str(retry_after)},
    )


def record_account_login_failure(user: User) -> bool:
    settings = get_settings()
    clear_expired_account_lock(user)
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.LOGIN_MAX_FAILURES_PER_ACCOUNT:
        user.login_locked_until = utc_now() + timedelta(minutes=settings.LOGIN_ACCOUNT_LOCK_MINUTES)
        user.failed_login_attempts = 0
        return True
    return False


def clear_account_login_failures(user: User) -> None:
    user.failed_login_attempts = 0
    user.login_locked_until = None
