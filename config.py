import os
import secrets
from datetime import timedelta


def _load_or_create_key(env_name, filename):
    key = os.environ.get(env_name)
    if key:
        return key

    keyfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", filename)
    if os.path.exists(keyfile):
        with open(keyfile, "r") as f:
            return f.read().strip()

    key = secrets.token_hex(32)
    os.makedirs(os.path.dirname(keyfile), exist_ok=True)
    with open(keyfile, "w") as f:
        f.write(key)
    os.chmod(keyfile, 0o600)
    return key


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = _load_or_create_key("DIARY_SECRET_KEY", ".secret_key")
    WTF_CSRF_SECRET_KEY = _load_or_create_key("DIARY_CSRF_KEY", ".csrf_key")
    ENCRYPTION_KEY = _load_or_create_key("DIARY_ENC_KEY", ".enc_key")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DIARY_DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'data', 'riji.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "check_same_thread": False,
            "timeout": 30,
        },
        "pool_size": 5,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

    SESSION_COOKIE_SECURE = os.environ.get("DIARY_SECURE_COOKIE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    WTF_CSRF_TIME_LIMIT = 3600

    BACKUP_DIR = os.path.join(BASE_DIR, "backups")
    BACKUP_INTERVAL_HOURS = 24
    BACKUP_KEEP_COUNT = 30

    LOGIN_ATTEMPT_LIMIT = 5
    LOGIN_ATTEMPT_WINDOW = 600  # 10 minutes


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
