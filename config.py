# app/config.py

from functools import lru_cache

try:
    from typing import Optional
except ImportError:  # Python 2.7 fallback
    Optional = None

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ==============================
    # Application
    # ==============================
    APP_NAME = "Inventory Intelligence Platform"
    ENVIRONMENT = "local"

    # ==============================
    # Database
    # ==============================
    DATABASE_URL = "sqlite:///./inventory.db"

    # ==============================
    # WhatsApp Configuration
    # ==============================
    WHATSAPP_API_URL = None
    WHATSAPP_ACCESS_TOKEN = None

    # ==============================
    # Alert Recipients
    # ==============================
    FOUNDER_PHONE = ""
    CO_FOUNDER_PHONE = ""

    # ==============================
    # ML
    # ==============================
    ML_ALERT_THRESHOLD = 0.75

    # ==============================
    # Security
    # ==============================
    FOUNDER_API_KEY = None

    class Config:
        env_file = ".env"


_optional_str = Optional[str] if Optional is not None else str

Settings.__annotations__ = {
    "APP_NAME": str,
    "ENVIRONMENT": str,
    "DATABASE_URL": str,
    "WHATSAPP_API_URL": _optional_str,
    "WHATSAPP_ACCESS_TOKEN": _optional_str,
    "FOUNDER_PHONE": str,
    "CO_FOUNDER_PHONE": str,
    "ML_ALERT_THRESHOLD": float,
    "FOUNDER_API_KEY": _optional_str,
}


@lru_cache
def get_settings():
    """
    Cached settings loader.
    Loaded once per process.
    """
    return Settings()
