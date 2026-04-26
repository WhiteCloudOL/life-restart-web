from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import Depends, HTTPException
from starlette.requests import Request

from app.core.app_config import get_app_config
from app.services.login_guard import get_request_ip


@dataclass(frozen=True)
class RateLimitRule:
    scope: str
    window_seconds: int
    max_requests: int


_request_buckets: dict[str, deque[datetime]] = defaultdict(deque)
_request_bucket_lock = Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_rate_limit_key(request: Request, rule: RateLimitRule) -> str:
    client_ip = get_request_ip(request)
    route_path = request.url.path
    return f"{rule.scope}:{client_ip}:{route_path}"


def create_rate_limit_dependency(rule_factory: Callable[[], RateLimitRule]):
    async def dependency(request: Request) -> None:
        rule = rule_factory()
        current_time = _utc_now()
        window_start = current_time - timedelta(seconds=rule.window_seconds)
        bucket_key = _build_rate_limit_key(request, rule)

        with _request_bucket_lock:
            bucket = _request_buckets[bucket_key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= rule.max_requests:
                retry_after = max(1, int((bucket[0] - window_start).total_seconds()))
                raise HTTPException(
                    status_code=429,
                    detail="请求过于频繁，请稍后重试",
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(current_time)

    return dependency


def get_auth_rate_limit_rule() -> RateLimitRule:
    config = get_app_config().rate_limit
    return RateLimitRule(
        scope="auth",
        window_seconds=config.auth_window_seconds,
        max_requests=config.auth_max_requests,
    )


def get_gameplay_rate_limit_rule() -> RateLimitRule:
    config = get_app_config().rate_limit
    return RateLimitRule(
        scope="gameplay",
        window_seconds=config.gameplay_window_seconds,
        max_requests=config.gameplay_max_requests,
    )


def get_profile_rate_limit_rule() -> RateLimitRule:
    config = get_app_config().rate_limit
    return RateLimitRule(
        scope="profile",
        window_seconds=config.profile_window_seconds,
        max_requests=config.profile_max_requests,
    )


def get_admin_rate_limit_rule() -> RateLimitRule:
    config = get_app_config().rate_limit
    return RateLimitRule(
        scope="admin",
        window_seconds=config.admin_window_seconds,
        max_requests=config.admin_max_requests,
    )


auth_rate_limiter = Depends(create_rate_limit_dependency(get_auth_rate_limit_rule))
gameplay_rate_limiter = Depends(create_rate_limit_dependency(get_gameplay_rate_limit_rule))
profile_rate_limiter = Depends(create_rate_limit_dependency(get_profile_rate_limit_rule))
admin_rate_limiter = Depends(create_rate_limit_dependency(get_admin_rate_limit_rule))
