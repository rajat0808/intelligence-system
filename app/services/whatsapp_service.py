import json
import re
from urllib import error, request

from app.config import get_settings


_NON_DIGIT_RE = re.compile(r"\D+")


def _normalize_graph_phone(phone):
    digits = _NON_DIGIT_RE.sub("", phone)
    return digits


def _build_payload(api_url, message, phone):
    if "graph.facebook.com" in api_url.lower():
        normalized_phone = _normalize_graph_phone(phone)
        if not normalized_phone:
            raise ValueError("phone is required")
        return {
            "messaging_product": "whatsapp",
            "to": normalized_phone,
            "type": "text",

            "text": {"body": message},
        }
    return {"to": phone, "message": message}


def _raise_http_error(exc):
    body = ""
    try:
        body_bytes = exc.read()
        if body_bytes:
            body = body_bytes.decode("utf-8", errors="replace").strip()
    # noinspection PyBroadException
    except Exception:
        body = ""

    if body:
        raise RuntimeError(
            "WhatsApp API error: HTTP {} {}".format(exc.code, body)
        ) from exc
    raise RuntimeError("WhatsApp API error: HTTP {}".format(exc.code)) from exc


def send_whatsapp(message, phone):
    settings = get_settings()

    api_url = (settings.WHATSAPP_API_URL or "").strip()
    access_token = (settings.WHATSAPP_ACCESS_TOKEN or "").strip()

    if not api_url:
        raise RuntimeError("WHATSAPP_API_URL is not configured")
    if not access_token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not configured")

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

    payload = json.dumps(_build_payload(api_url, message, phone)).encode("utf-8")

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
        with request.urlopen(req, timeout=15) as response:
            status_code = response.getcode()
            if status_code < 200 or status_code >= 300:
                raise RuntimeError("WhatsApp API error: HTTP {}".format(status_code))
    except error.HTTPError as exc:
        _raise_http_error(exc)
    except error.URLError as exc:
        raise RuntimeError("WhatsApp API error: {}".format(exc.reason)) from exc
