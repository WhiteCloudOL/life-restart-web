import json

from sqlalchemy import text
from sqlmodel import Session, SQLModel, select

from app.core.app_config import get_app_config
from app.core.world_config import StartupPresetConfig
from app.core.world_config import get_world_config
from app.core.security import encrypt_user_secret, is_encrypted_secret
from app.core.security import hash_password, validate_password_strength
from app.db.session import engine
from app.models.preset import Preset
from app.models.user import User


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    migrate_user_quota_columns()


def migrate_user_quota_columns() -> None:
    """
    为历史数据库补齐新增额度字段（幂等）。
    """
    app_config = get_app_config()
    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(user)")).fetchall()
        column_names = {str(row[1]) for row in columns}

        if "daily_model_call_limit" not in column_names:
            conn.execute(
                text(
                    "ALTER TABLE user ADD COLUMN daily_model_call_limit INTEGER NOT NULL DEFAULT 80"
                )
            )
        if "used_model_calls_today" not in column_names:
            conn.execute(
                text(
                    "ALTER TABLE user ADD COLUMN used_model_calls_today INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "nickname" not in column_names:
            conn.execute(text("ALTER TABLE user ADD COLUMN nickname VARCHAR(32)"))
        if "api_mode" not in column_names:
            conn.execute(
                text("ALTER TABLE user ADD COLUMN api_mode VARCHAR(16) NOT NULL DEFAULT 'default'")
            )
        if "failed_login_attempts" not in column_names:
            conn.execute(
                text("ALTER TABLE user ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0")
            )
        if "login_locked_until" not in column_names:
            conn.execute(text("ALTER TABLE user ADD COLUMN login_locked_until DATETIME"))

        conn.execute(
            text(
                "UPDATE user SET daily_model_call_limit = :default_limit "
                "WHERE daily_model_call_limit IS NULL OR daily_model_call_limit < 0"
            ),
            {"default_limit": app_config.quota.default_daily_model_call_limit},
        )
        conn.execute(
            text(
                "UPDATE user SET used_model_calls_today = 0 "
                "WHERE used_model_calls_today IS NULL OR used_model_calls_today < 0"
            )
        )
        conn.execute(
            text(
                "UPDATE user SET nickname = username "
                "WHERE nickname IS NULL OR TRIM(nickname) = ''"
            )
        )
        conn.execute(
            text(
                "UPDATE user SET api_mode = 'default' "
                "WHERE api_mode IS NULL OR api_mode NOT IN ('default', 'custom')"
            )
        )
        conn.execute(
            text(
                "UPDATE user SET failed_login_attempts = 0 "
                "WHERE failed_login_attempts IS NULL OR failed_login_attempts < 0"
            )
        )


def seed_default_presets() -> None:
    world_config = get_world_config()
    configured_presets = list(world_config.startup_presets)
    custom_preset = world_config.custom_preset
    if custom_preset and custom_preset.enabled:
        configured_presets.append(
            StartupPresetConfig.model_validate(
                {
                    "id": custom_preset.id,
                    "title": custom_preset.title,
                    "description": custom_preset.description,
                    "worldview": custom_preset.default_worldview or "由玩家自定义世界设定",
                    "character_options": [],
                    "attributes": [item.model_dump() for item in custom_preset.attributes],
                    "max_attribute_points": custom_preset.max_attribute_points,
                    "start_age": custom_preset.start_age,
                    "age_step": custom_preset.age_step,
                    "is_custom": True,
                }
            )
        )
    with Session(engine) as session:
        db_rows = {row.id: row for row in session.exec(select(Preset)).all() if row.id is not None}
        changed = False

        for preset in configured_presets:
            initial_stats = {
                item.key: item.default_value
                for item in preset.attributes
            }
            if preset.id in db_rows:
                row = db_rows[preset.id]
                row.title = preset.title
                row.description = preset.description
                row.initial_stats = json.dumps(initial_stats, ensure_ascii=False)
                session.add(row)
                changed = True
                continue

            session.add(
                Preset(
                    id=preset.id,
                    title=preset.title,
                    description=preset.description,
                    initial_stats=json.dumps(initial_stats, ensure_ascii=False),
                )
            )
            changed = True

        if changed:
            session.commit()


def seed_default_admin() -> None:
    """
    按业务配置创建默认管理员账号。
    仅在用户名不存在时创建，避免覆盖已有账号密码。
    """
    app_config = get_app_config()
    username = app_config.default_admin.username.strip()
    password = app_config.default_admin.password
    if not username or not password:
        return

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            return
        try:
            validate_password_strength(password)
            hashed_password = hash_password(password)
        except ValueError as exc:
            print(f"[init_db] 默认管理员创建失败：{exc}")
            return
        session.add(
            User(
                username=username,
                nickname=username,
                hashed_password=hashed_password,
                is_admin=True,
                daily_quota=app_config.quota.max_daily_quota,
                daily_model_call_limit=app_config.quota.max_daily_model_call_limit,
            )
        )
        session.commit()


def migrate_user_secret_storage() -> None:
    """
    将历史明文 custom_api_key 平滑迁移为密文存储。
    迁移策略：
    - 仅处理非空、且未加密的数据
    - 幂等：已迁移数据不会重复处理
    """
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        changed = False
        for user in users:
            if not user.custom_api_key:
                continue
            if is_encrypted_secret(user.custom_api_key):
                continue
            user.custom_api_key = encrypt_user_secret(user.custom_api_key)
            session.add(user)
            changed = True
        if changed:
            session.commit()
