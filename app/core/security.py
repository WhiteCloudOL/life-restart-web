import base64
import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import TypedDict, cast
from uuid import uuid4

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

ENCRYPTED_SECRET_PREFIX = "enc::"


class AccessTokenClaims(TypedDict):
    sub: str
    type: str
    iat: int
    nbf: int
    exp: int
    jti: str


def validate_username(username: str) -> str:
    username = username.strip()
    if not 3 <= len(username) <= 32:
        raise ValueError("用户名长度必须在 3 到 32 字符之间")
    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        raise ValueError("用户名只能包含字母、数字和下划线")
    return username


def validate_password_strength(password: str) -> None:
    if len(password) < 10:
        raise ValueError("密码长度至少 10 位")
    if not re.search(r"[A-Z]", password):
        raise ValueError("密码必须包含至少 1 个大写字母")
    if not re.search(r"[a-z]", password):
        raise ValueError("密码必须包含至少 1 个小写字母")
    if not re.search(r"\d", password):
        raise ValueError("密码必须包含至少 1 个数字")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("密码必须包含至少 1 个特殊字符")
    lowered = password.lower()
    weak_words = ("password", "qwerty", "admin", "123456")
    if any(word in lowered for word in weak_words):
        raise ValueError("密码过于常见，请更换为更强密码")


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("密码过长：bcrypt 最多支持 72 字节")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: AccessTokenClaims = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()
    raw_payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "type", "iat", "nbf", "jti"]},
    )
    payload = cast(AccessTokenClaims, raw_payload)
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("token type invalid")
    return payload


def _build_fernet() -> Fernet:
    settings = get_settings()
    # 用 SHA-256 派生固定长度密钥，再转成 Fernet 所需的 URL-safe Base64
    digest = hashlib.sha256(settings.USER_DATA_ENCRYPTION_SECRET.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def is_encrypted_secret(value: str | None) -> bool:
    return bool(value and value.startswith(ENCRYPTED_SECRET_PREFIX))


def encrypt_user_secret(plain_text: str) -> str:
    encrypted = _build_fernet().encrypt(plain_text.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTED_SECRET_PREFIX}{encrypted}"


def decrypt_user_secret(cipher_text: str | None) -> str | None:
    if not cipher_text:
        return None

    # 兼容历史明文（用于平滑迁移），读取后会在写入流程中转为密文
    if not is_encrypted_secret(cipher_text):
        return cipher_text

    raw = cipher_text[len(ENCRYPTED_SECRET_PREFIX) :]
    try:
        return _build_fernet().decrypt(raw.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def has_usable_user_secret(cipher_text: str | None) -> bool:
    plain = decrypt_user_secret(cipher_text)
    return bool((plain or "").strip())
