import json
import re
from urllib import error, request
from urllib.parse import urlparse

from app.config import get_settings


_NON_DIGIT_RE = re.compile(r"\D+")
_ABSOLUTE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_ALLOWED_HTTP_SCHEMES = {"http", "https"}


def _is_graph_api_url(api_url):
    return "graph.facebook.com" in api_url.lower()


def _normalize_country_code(value):
    digits = _NON_DIGIT_RE.sub("", str(value or ""))
    return digits


def _normalize_graph_phone(phone, default_country_code=None):
    digits = _NON_DIGIT_RE.sub("", phone)
    country_code = _normalize_country_code(default_country_code)
    if country_code and len(digits) == 10:
        return country_code + digits
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


def _normalize_required(value, field_name):
    if value is None:
        raise ValueError("{} is required".format(field_name))
    normalized_value = str(value).strip()
    if not normalized_value:
        raise ValueError("{} is required".format(field_name))
    return normalized_value


def _resolve_whatsapp_config(api_url=None, access_token=None, media_base_url=None):
    settings = get_settings()

    resolved_api_url = str(
        api_url if api_url is not None else (settings.WHATSAPP_API_URL or "")
    ).strip()
    resolved_access_token = str(
        access_token if access_token is not None else (settings.WHATSAPP_ACCESS_TOKEN or "")
    ).strip()
    resolved_media_base_url = str(
        media_base_url
        if media_base_url is not None
        else (settings.WHATSAPP_MEDIA_BASE_URL or "")
    ).strip()
    resolved_default_country_code = _normalize_country_code(
        settings.WHATSAPP_DEFAULT_COUNTRY_CODE
    )

    if not resolved_api_url:
        raise RuntimeError("WHATSAPP_API_URL is not configured")
    if not resolved_access_token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not configured")

    return (
        _validate_api_url(resolved_api_url),
        resolved_access_token,
        resolved_media_base_url,
        resolved_default_country_code,
    )


def _build_payload(
    api_url,
    message,
    phone,
    image_url=None,
    default_country_code=None,
):
    if _is_graph_api_url(api_url):
        normalized_phone = _normalize_graph_phone(phone, default_country_code)
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


def build_payload(
    api_url,
    message,
    phone,
    image_url=None,
    default_country_code=None,
):
    return _build_payload(
        api_url,
        message,
        phone,
        image_url,
        default_country_code=default_country_code,
    )


def _build_template_payload(
    api_url,
    phone,
    template_name,
    language_code,
    store_id,
    category,
    department,
    transfer_to,
    aging_system_rule,
    image_url=None,
    default_country_code=None,
):
    if not _is_graph_api_url(api_url):
        raise ValueError("Template messaging requires a graph.facebook.com API URL")

    normalized_phone = _normalize_graph_phone(phone, default_country_code)
    if not normalized_phone:
        raise ValueError("phone is required")

    components = []
    if image_url:
        components.append(
            {
                "type": "header",
                "parameters": [{"type": "image", "image": {"link": image_url}}],
            }
        )
    components.append(
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": store_id},
                {"type": "text", "text": category},
                {"type": "text", "text": department},
                {"type": "text", "text": transfer_to},
                {"type": "text", "text": aging_system_rule},
            ],
        }
    )

    return {
        "messaging_product": "whatsapp",
        "to": normalized_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components,
        },
    }


def build_template_payload(
    api_url,
    phone,
    template_name,
    language_code,
    store_id,
    category,
    department,
    transfer_to,
    aging_system_rule,
    image_url=None,
    default_country_code=None,
):
    return _build_template_payload(
        api_url=api_url,
        phone=phone,
        template_name=template_name,
        language_code=language_code,
        store_id=store_id,
        category=category,
        department=department,
        transfer_to=transfer_to,
        aging_system_rule=aging_system_rule,
        image_url=image_url,
        default_country_code=default_country_code,
    )


def _validate_api_url(api_url):
    parsed = urlparse(api_url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_HTTP_SCHEMES or not parsed.netloc:
        raise RuntimeError("WHATSAPP_API_URL must be an absolute HTTP(S) URL")
    return api_url


def validate_api_url(api_url):
    return _validate_api_url(api_url)


def _build_auth_header(access_token):
    if access_token.lower().startswith("bearer "):
        return access_token
    return "Bearer {}".format(access_token)


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


def _post_whatsapp_payload(api_url, access_token, payload_obj):
    payload = json.dumps(payload_obj).encode("utf-8")

    req = request.Request(
        api_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _build_auth_header(access_token),
        },
    )

    try:
        with request.urlopen(req, timeout=15) as response:  # no sec B310
            status_code = response.getcode()
            if status_code < 200 or status_code >= 300:
                raise RuntimeError("WhatsApp API error: HTTP {}".format(status_code))
    except error.HTTPError as exc:
        _raise_http_error(exc)
    except error.URLError as exc:
        raise RuntimeError("WhatsApp API error: {}".format(exc.reason)) from exc


def send_whatsapp(
    message,
    phone,
    image_url=None,
    *,
    api_url=None,
    access_token=None,
    media_base_url=None,
):
    (
        resolved_api_url,
        resolved_access_token,
        resolved_media_base_url,
        resolved_default_country_code,
    ) = _resolve_whatsapp_config(
        api_url=api_url,
        access_token=access_token,
        media_base_url=media_base_url,
    )

    message_value = _normalize_required(message, "message")
    phone_value = _normalize_required(phone, "phone")

    media_url = _resolve_media_url(image_url, resolved_media_base_url)
    payload_obj = _build_payload(
        resolved_api_url,
        message_value,
        phone_value,
        media_url,
        default_country_code=resolved_default_country_code,
    )
    _post_whatsapp_payload(resolved_api_url, resolved_access_token, payload_obj)


def send_whatsapp_template(
    phone,
    store_id,
    category,
    department,
    transfer_to,
    aging_system_rule,
    image_url=None,
    template_name="inventory_transfer_alert",
    language_code="en",
    *,
    api_url=None,
    access_token=None,
    media_base_url=None,
):
    (
        resolved_api_url,
        resolved_access_token,
        resolved_media_base_url,
        resolved_default_country_code,
    ) = _resolve_whatsapp_config(
        api_url=api_url,
        access_token=access_token,
        media_base_url=media_base_url,
    )

    phone_value = _normalize_required(phone, "phone")
    template_name_value = _normalize_required(template_name, "template_name")
    language_code_value = _normalize_required(language_code, "language_code")

    payload_obj = _build_template_payload(
        api_url=resolved_api_url,
        phone=phone_value,
        template_name=template_name_value,
        language_code=language_code_value,
        store_id=_normalize_required(store_id, "store_id"),
        category=_normalize_required(category, "category"),
        department=_normalize_required(department, "department"),
        transfer_to=_normalize_required(transfer_to, "transfer_to"),
        aging_system_rule=_normalize_required(aging_system_rule, "aging_system_rule"),
        image_url=_resolve_media_url(image_url, resolved_media_base_url),
        default_country_code=resolved_default_country_code,
    )
    _post_whatsapp_payload(resolved_api_url, resolved_access_token, payload_obj)
