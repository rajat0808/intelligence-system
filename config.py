from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

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
    # WhatsApp Configuration
    # ==============================
    WHATSAPP_API_URL: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None

    # ==============================
    # Alert Recipients
    # ==============================
    FOUNDER_PHONE: str = ""
    CO_FOUNDER_PHONE: str = ""

    # ==============================
    # ML
    # ==============================
    ML_ALERT_THRESHOLD: float = 0.75

    # ==============================
    # Excel Auto-Import
    # ==============================
    EXCEL_AUTO_IMPORT: bool = True
    EXCEL_DATASOURCE_DIR: str = "datasource"
    EXCEL_POLL_SECONDS: int = 10
    EXCEL_IMPORT_SHEETS: Optional[str] = None

    # ==============================
    # Security
    # ==============================
    FOUNDER_API_KEY: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings loader.
    Loaded once per process.
    """
    return Settings()
