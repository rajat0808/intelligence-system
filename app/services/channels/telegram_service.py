import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{}/sendMessage"
_TELEGRAM_SEND_PHOTO_URL = "https://api.telegram.org/bot{}/sendPhoto"
_TELEGRAM_SEND_DOCUMENT_URL = "https://api.telegram.org/bot{}/sendDocument"
_REQUEST_TIMEOUT_SECONDS = 10
_APP_ROOT = Path(__file__).resolve().parents[3]
_STATIC_DIR = _APP_ROOT / "app" / "static"
_DEFAULT_FALLBACK_IMAGE = "/static/sindh-logo.png"
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

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


def _apply_template(message_text: str) -> str:
    template_value = str(os.getenv("TELEGRAM_ALERT_TEMPLATE") or "").strip()
    if not template_value:
        return message_text
    template_value = template_value.replace("\\n", "\n")

    if "{message}" in template_value:
        return template_value.replace("{message}", message_text)

    logger.warning(
        "TELEGRAM_ALERT_TEMPLATE does not include '{message}'. Appending message."
    )
    return "{}\n{}".format(template_value, message_text)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _find_static_image_by_stem(value: str) -> Path | None:
    image_stem = Path(str(value or "").strip()).stem.strip()
    if not image_stem:
        return None

    images_dir = _STATIC_DIR / "images"
    if not images_dir.exists():
        return None

    for extension in _IMAGE_EXTENSIONS:
        direct_candidate = images_dir / f"{image_stem}{extension}"
        if direct_candidate.exists() and direct_candidate.is_file():
            return direct_candidate

    image_stem_lower = image_stem.lower()
    try:
        for image_path in images_dir.iterdir():
            if not image_path.is_file():
                continue
            if image_path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue
            if image_path.stem.lower() == image_stem_lower:
                return image_path
    except OSError:
        return None

    return None


def _resolve_image_source(image_url: Any) -> tuple[str, str | Path] | None:
    image_value = str(image_url or "").strip()
    if not image_value:
        return None

    if _is_http_url(image_value):
        return ("remote", image_value)

    normalized_path = image_value.replace("\\", "/").strip()
    if normalized_path.startswith("/static/"):
        path_value = _APP_ROOT / "app" / normalized_path.lstrip("/")
    elif normalized_path.startswith("static/"):
        path_value = _APP_ROOT / "app" / normalized_path
    elif normalized_path.startswith("images/"):
        path_value = _STATIC_DIR / normalized_path.removeprefix("images/")
    else:
        candidate = Path(image_value)
        if not candidate.is_absolute():
            candidate = _APP_ROOT / image_value.lstrip("/\\")
        path_value = candidate

    if path_value.exists() and path_value.is_file():
        return ("local", path_value)

    static_image_path = _find_static_image_by_stem(normalized_path)
    if static_image_path is not None:
        return ("local", static_image_path)

    # Preserve raw datasource reference for Telegram-native media identifiers.
    return ("telegram_ref", image_value)


def _resolve_fallback_image_source() -> tuple[str, str | Path] | None:
    fallback_image = str(os.getenv("TELEGRAM_FALLBACK_IMAGE") or _DEFAULT_FALLBACK_IMAGE).strip()
    if not fallback_image:
        return None
    return _resolve_image_source(fallback_image)


def _is_success_response(response: requests.Response) -> bool:
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


def _send_photo(
    token: str,
    chat_id: str,
    caption: str,
    image_source: tuple[str, str | Path],
) -> bool:
    source_kind, source_value = image_source
    photo_payload = {
        "chat_id": chat_id,
        "caption": caption[:1024],
    }
    photo_url = _TELEGRAM_SEND_PHOTO_URL.format(token)

    try:
        if source_kind == "local":
            image_path = Path(source_value)
            with image_path.open("rb") as image_file:
                response = requests.post(
                    photo_url,
                    data=photo_payload,
                    files={"photo": (image_path.name, image_file)},
                    timeout=_REQUEST_TIMEOUT_SECONDS,
                )
        else:
            response = requests.post(
                photo_url,
                data={**photo_payload, "photo": str(source_value)},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(
            "Telegram photo API request failed for source '%s': %s",
            source_kind,
            exc,
        )
        return False

    return _is_success_response(response)


def send_telegram_alert(message: str, image_url: Any = None) -> bool:
    token, chat_id = _resolve_telegram_config()
    if not token or not chat_id:
        return False

    message_text = str(message or "").strip()
    if not message_text:
        logger.warning("Telegram alert skipped: message is empty.")
        return False

    formatted_message = _apply_template(message_text)
    if image_url is not None:
        image_sources = []
        primary_source = _resolve_image_source(image_url)
        if primary_source is not None:
            image_sources.append(primary_source)

        fallback_source = _resolve_fallback_image_source()
        if fallback_source is not None and fallback_source not in image_sources:
            image_sources.append(fallback_source)

        for image_source in image_sources:
            if _send_photo(token, chat_id, formatted_message, image_source):
                return True

    text_payload = {
        "chat_id": chat_id,
        "text": formatted_message,
    }
    text_url = _TELEGRAM_SEND_MESSAGE_URL.format(token)

    try:
        response = requests.post(text_url, json=text_payload, timeout=_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Telegram API request failed.")
        return False

    return _is_success_response(response)


def send_telegram_document(file_path: str | Path, caption: str | None = None) -> bool:
    token, chat_id = _resolve_telegram_config()
    if not token or not chat_id:
        return False

    document_path = Path(file_path)
    if not document_path.exists() or not document_path.is_file():
        logger.warning("Telegram document send skipped: file not found '%s'.", document_path)
        return False

    payload = {"chat_id": chat_id}
    caption_text = str(caption or "").strip()
    if caption_text:
        payload["caption"] = caption_text[:1024]

    document_url = _TELEGRAM_SEND_DOCUMENT_URL.format(token)
    try:
        with document_path.open("rb") as document_file:
            response = requests.post(
                document_url,
                data=payload,
                files={"document": (document_path.name, document_file, "application/pdf")},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
    except requests.RequestException:
        logger.exception("Telegram document API request failed.")
        return False

    return _is_success_response(response)


__all__ = ["send_telegram_alert", "send_telegram_document"]
