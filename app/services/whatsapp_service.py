import json
import re
from urllib import error, request
from urllib.parse import urlparse

from app.config import get_settings


_NON_DIGIT_RE = re.compile(r"\D+")
_ABSOLUTE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_ALLOWED_HTTP_SCHEMES = {"http", "https"}


def _normalize_graph_phone(phone):
    digits = _NON_DIGIT_RE.sub("", phone)
    return digits


def _resolve_media_url(image_url, media_base_url):
    if image_url is None:
        return None
    image_value = str(image_url).strip()
    if not image_value:
        return None
    if _ABSOLUTE_URL_RE.match(image_value):
        return image_value

    base_value = str(media_base_url or "").strip()
    if not base_value:
        return None

    normalized_path = image_value.replace("\\", "/").strip()
    lower_path = normalized_path.lower()
    if lower_path.startswith("images/"):
        normalized_path = "/static/" + normalized_path.lstrip("/")
    elif lower_path.startswith("static/"):
        normalized_path = "/" + normalized_path.lstrip("/")
    elif not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path.lstrip("/")

    return base_value.rstrip("/") + normalized_path


def resolve_media_url(image_url, media_base_url):
    return _resolve_media_url(image_url, media_base_url)


def _build_payload(api_url, message, phone, image_url=None):
    if "graph.facebook.com" in api_url.lower():
        normalized_phone = _normalize_graph_phone(phone)
        if not normalized_phone:
            raise ValueError("phone is required")
        if image_url:
            return {
                "messaging_product": "whatsapp",
                "to": normalized_phone,
                "type": "image",
                "image": {"link": image_url, "caption": message},
            }
        return {
            "messaging_product": "whatsapp",
            "to": normalized_phone,
            "type": "text",
            "text": {"body": message},
        }
    payload = {"to": phone, "message": message}
    if image_url:
        payload["media_url"] = image_url
    return payload


def build_payload(api_url, message, phone, image_url=None):
    return _build_payload(api_url, message, phone, image_url)


def _validate_api_url(api_url):
    parsed = urlparse(api_url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_HTTP_SCHEMES or not parsed.netloc:
        raise RuntimeError("WHATSAPP_API_URL must be an absolute HTTP(S) URL")
    return api_url


def validate_api_url(api_url):
    return _validate_api_url(api_url)


def _raise_http_error(exc):
    body = ""
    try:
        body_bytes = exc.read()
        if body_bytes:
            body = body_bytes.decode("utf-8", errors="replace").strip()
    except (OSError, ValueError):
        body = ""

    if body:
        raise RuntimeError(
            "WhatsApp API error: HTTP {} {}".format(exc.code, body)
        ) from exc
    raise RuntimeError("WhatsApp API error: HTTP {}".format(exc.code)) from exc


def send_whatsapp(message, phone, image_url=None):
    settings = get_settings()

    api_url = (settings.WHATSAPP_API_URL or "").strip()
    access_token = (settings.WHATSAPP_ACCESS_TOKEN or "").strip()
    media_base_url = (settings.WHATSAPP_MEDIA_BASE_URL or "").strip()

    if not api_url:
        raise RuntimeError("WHATSAPP_API_URL is not configured")
    if not access_token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not configured")
    api_url = _validate_api_url(api_url)

    if message is None:
        raise ValueError("message is required")
    if phone is None:
        raise ValueError("phone is required")

    message = str(message).strip()
    phone = str(phone).strip()
    if not message:
        raise ValueError("message is required")
    if not phone:
        raise ValueError("phone is required")

    media_url = _resolve_media_url(image_url, media_base_url)
    payload = json.dumps(_build_payload(api_url, message, phone, media_url)).encode("utf-8")

    if access_token.lower().startswith("bearer "):
        auth_header = access_token
    else:
        auth_header = "Bearer {}".format(access_token)

    req = request.Request(
        api_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
        },
    )

    try:
        with request.urlopen(req, timeout=15) as response:  # nosec B310
            status_code = response.getcode()
            if status_code < 200 or status_code >= 300:
                raise RuntimeError("WhatsApp API error: HTTP {}".format(status_code))
    except error.HTTPError as exc:
        _raise_http_error(exc)
    except error.URLError as exc:
        raise RuntimeError("WhatsApp API error: {}".format(exc.reason)) from exc
