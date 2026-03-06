import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{}/sendMessage"
_REQUEST_TIMEOUT_SECONDS = 10

load_dotenv()


def _normalize_required(value: Any, field_name: str) -> str | None:
    if value is None:
        logger.warning("Telegram alert skipped: %s is not configured.", field_name)
        return None
    normalized_value = str(value).strip()
    if not normalized_value:
        logger.warning("Telegram alert skipped: %s is not configured.", field_name)
        return None
    return normalized_value


def _resolve_telegram_config() -> tuple[str | None, str | None]:
    token = _normalize_required(os.getenv("TELEGRAM_BOT_TOKEN"), "TELEGRAM_BOT_TOKEN")
    chat_id = _normalize_required(os.getenv("TELEGRAM_CHAT_ID"), "TELEGRAM_CHAT_ID")
    return token, chat_id


def send_telegram_alert(message: str) -> bool:
    token, chat_id = _resolve_telegram_config()
    if not token or not chat_id:
        return False

    message_text = str(message or "").strip()
    if not message_text:
        logger.warning("Telegram alert skipped: message is empty.")
        return False

    payload = {
        "chat_id": chat_id,
        "text": message_text,
    }
    api_url = _TELEGRAM_SEND_MESSAGE_URL.format(token)

    try:
        response = requests.post(api_url, json=payload, timeout=_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Telegram API request failed.")
        return False

    try:
        response_payload = response.json()
    except ValueError:
        logger.error(
            "Telegram API returned non-JSON response. status_code=%s",
            response.status_code,
        )
        return False

    if not isinstance(response_payload, dict):
        logger.error(
            "Telegram API returned unsupported payload type: %s",
            type(response_payload).__name__,
        )
        return False

    if not response_payload.get("ok"):
        logger.error("Telegram API returned an error response: %s", response_payload)
        return False

    return True


__all__ = ["send_telegram_alert"]
