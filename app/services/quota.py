from datetime import datetime, timezone

from fastapi import HTTPException

from app.models.user import User


def utc_today():
    return datetime.now(timezone.utc).date()


def reset_quota_if_new_day(user: User) -> None:
    """
    跨天自动重置额度：
    1. 若 last_active_date 不是今天（UTC），将当日计数归零
    2. 更新 last_active_date，避免重复重置
    """
    today = utc_today()
    if user.last_active_date != today:
        user.used_quota_today = 0
        user.used_model_calls_today = 0
        user.last_active_date = today


def enforce_world_entry_quota(user: User, unlimited: bool = False) -> None:
    """
    额度校验：
    - 先处理跨天重置
    - 当用量超限且用户未配置 custom_api_key 时，抛出 429
    """
    reset_quota_if_new_day(user)
    if unlimited:
        return
    if user.used_quota_today >= user.daily_quota:
        raise HTTPException(status_code=429, detail="今日进入世界次数已耗尽")


def enforce_model_call_quota(user: User, unlimited: bool = False) -> None:
    """
    模型调用次数校验：
    - 先处理跨天重置
    - 默认模型用户超限时抛出 429
    """
    reset_quota_if_new_day(user)
    if unlimited:
        return
    if user.used_model_calls_today >= user.daily_model_call_limit:
        raise HTTPException(status_code=429, detail="今日模型调用次数已耗尽")


def consume_world_entry_quota(user: User, unlimited: bool = False) -> None:
    """
    扣减额度（准确说是计数+1）：
    - 进入世界成功后执行（非每次模型调用）
    """
    if unlimited:
        user.last_active_date = utc_today()
        return
    user.used_quota_today += 1
    user.last_active_date = utc_today()


def consume_model_call_quota(user: User, unlimited: bool = False) -> None:
    """
    记录模型调用次数：
    - 仅在调用成功后计数（失败不计数）
    """
    if unlimited:
        user.last_active_date = utc_today()
        return
    user.used_model_calls_today += 1
    user.last_active_date = utc_today()
