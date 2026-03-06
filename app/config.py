from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ==============================
    # Application
    # ==============================
    APP_NAME: str = "Inventory Intelligence Platform"
    ENVIRONMENT: str = "local"

    # ==============================
    # Database
    # ==============================
    DATABASE_URL: str = "sqlite:///./inventory.db"

    # ==============================
    # Logging
    # ==============================
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # ==============================
    # Security
    # ==============================
    FOUNDER_API_KEY: Optional[str] = None
    API_KEYS: Optional[str] = None
    API_KEY_HEADER: str = "X-API-Key"
    JWT_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: Optional[str] = None
    JWT_ISSUER: Optional[str] = None
    JWT_REQUIRED: bool = False
    DASHBOARD_USERNAME: Optional[str] = None
    DASHBOARD_PASSWORD: Optional[str] = None
    DASHBOARD_PASSWORD_HASH: Optional[str] = None
    DASHBOARD_PASSWORD_SALT: Optional[str] = None
    DASHBOARD_PBKDF2_ROUNDS: int = 200_000
    DASHBOARD_SESSION_SECRET: Optional[str] = None
    DASHBOARD_SESSION_COOKIE: str = "iip_session"

    # ==============================
    # WhatsApp Configuration
    # ==============================
    WHATSAPP_API_URL: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_MEDIA_BASE_URL: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_DEFAULT_COUNTRY_CODE: Optional[str] = None
    WHATSAPP_NOTIFICATIONS_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_ALERT_TEMPLATE: Optional[str] = None
    TELEGRAM_FALLBACK_IMAGE: str = "/static/sindh-logo.png"

    # ==============================
    # Alert Recipients
    # ==============================
    FOUNDER_PHONE: str = ""
    CO_FOUNDER_PHONE: str = ""

    # ==============================
    # ML
    # ==============================
    ML_ALERT_THRESHOLD: float = 0.75
    ML_ALERT_HIGH_THRESHOLD: float = 0.85
    ML_ALERT_CRITICAL_THRESHOLD: float = 0.92
    ML_MODEL_PATH: Optional[str] = None
    ML_MODEL_METADATA_PATH: Optional[str] = None

    # ==============================
    # Alert Noise Controls
    # ==============================
    ALERT_MIN_CAPITAL_VALUE: float = 15000.0
    ALERT_COOLDOWN_DAYS: int = 2
    ALERT_MAX_PER_RECIPIENT_PER_RUN: int = 20
    ALERT_ALWAYS_SEND: bool = False
    LOW_STOCK_ALERT_THRESHOLD: int = 5

    # ==============================
    # Excel Auto-Import
    # ==============================
    EXCEL_AUTO_IMPORT: bool = True
    EXCEL_DATASOURCE_DIR: str = "datasource"
    EXCEL_POLL_SECONDS: int = 10
    EXCEL_IMPORT_SHEETS: Optional[str] = None
    EXCEL_DAILY_UPDATE_SHEET_ALIASES: Optional[str] = None
    EXCEL_CREATE_MISSING_STORES: bool = False

    # ==============================
    # Scheduler
    # ==============================
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_RUN_AFTER: str = "12:00"
    SCHEDULER_POLL_SECONDS: int = 30
    SCHEDULER_HEARTBEAT_SECONDS: int = 30
    SCHEDULER_STALE_SECONDS: int = 900
    SCHEDULER_RETRY_SECONDS: int = 300
    SCHEDULER_MAX_RETRIES: int = 3
    SCHEDULER_TZ: str = "local"
    SCHEDULER_RUN_ON_STARTUP: bool = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings loader (once per process)."""
    return Settings()


__all__ = ["Settings", "get_settings"]
