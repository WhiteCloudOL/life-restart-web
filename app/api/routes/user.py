from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_session
from app.core.security import encrypt_user_secret, has_usable_user_secret
from app.models.game_session import GameSession
from app.models.user import User
from app.schemas.game import GameSessionRead
from app.schemas.user import UserRead, UserUpdateRequest
from app.services.game_engine import parse_json_array, parse_json_object
from app.services.quota import reset_quota_if_new_day

router = APIRouter(prefix="/user", tags=["user"])


def to_user_read(user: User) -> UserRead:
    nickname = (user.nickname or "").strip() or user.username
    return UserRead(
        id=user.id,
        username=user.username,
        nickname=nickname,
        api_mode=user.api_mode if user.api_mode in {"default", "custom"} else "default",
        has_custom_api_key=has_usable_user_secret(user.custom_api_key),
        custom_model_name=user.custom_model_name,
        custom_base_url=user.custom_base_url,
        is_admin=user.is_admin,
        world_entry_limit=user.daily_quota,
        world_entries_used_today=user.used_quota_today,
        model_call_limit=user.daily_model_call_limit,
        model_calls_used_today=user.used_model_calls_today,
        last_active_date=user.last_active_date,
    )


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # 每次读取用户信息时做跨天重置，保证额度显示准确
    reset_quota_if_new_day(current_user)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return to_user_read(current_user)


@router.put("/me", response_model=UserRead)
def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if "nickname" in payload.model_fields_set:
        nickname = (payload.nickname or "").strip()
        current_user.nickname = nickname if nickname else current_user.username
    if "api_mode" in payload.model_fields_set and payload.api_mode is not None:
        current_user.api_mode = payload.api_mode

    if "custom_api_key" in payload.model_fields_set:
        # 自定义 Key 仅在服务端加密落库，避免明文存储
        trimmed = (payload.custom_api_key or "").strip()
        current_user.custom_api_key = encrypt_user_secret(trimmed) if trimmed else None
    if "custom_model_name" in payload.model_fields_set:
        model_name = (payload.custom_model_name or "").strip()
        current_user.custom_model_name = model_name if model_name else None
    if "custom_base_url" in payload.model_fields_set:
        current_user.custom_base_url = str(payload.custom_base_url) if payload.custom_base_url else None

    if current_user.api_mode == "custom":
        if not (current_user.custom_model_name or "").strip():
            raise HTTPException(status_code=400, detail="启用自定义 API 模式前请先填写自定义模型名")
        if not has_usable_user_secret(current_user.custom_api_key):
            raise HTTPException(status_code=400, detail="启用自定义 API 模式前请先填写自定义 API Key")

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return to_user_read(current_user)


@router.get("/history", response_model=List[GameSessionRead])
def my_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    sessions = session.exec(
        select(GameSession)
        .where(GameSession.user_id == current_user.id)
        .order_by(GameSession.id.desc())
    ).all()

    result: List[GameSessionRead] = []
    for row in sessions:
        result.append(
            GameSessionRead(
                id=row.id,
                user_id=row.user_id,
                preset_id=row.preset_id,
                current_stats=parse_json_object(row.current_stats),
                event_history=parse_json_array(row.event_history),
                is_ended=row.is_ended,
            )
        )
    return result
