import json
from urllib import error, request

from app.config import get_settings


def _build_payload(api_url, message, phone):
    if "graph.facebook.com" in api_url:
        return {
            "messaging_product": "whatsapp",
            "to": phone,
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

    if not settings.WHATSAPP_API_URL:
        raise RuntimeError("WHATSAPP_API_URL is not configured")
    if not settings.WHATSAPP_ACCESS_TOKEN:
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

    payload = json.dumps(
        _build_payload(settings.WHATSAPP_API_URL, message, phone)
    ).encode("utf-8")

    req = request.Request(
        settings.WHATSAPP_API_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(settings.WHATSAPP_ACCESS_TOKEN),
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
