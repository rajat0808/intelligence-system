import json
from urllib import request

from app.config import get_settings


def send_whatsapp(message, phone):
    settings = get_settings()

    if not settings.WHATSAPP_API_URL:
        raise RuntimeError("WHATSAPP_API_URL is not configured")
    if not settings.WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not configured")

    payload = json.dumps({"to": phone, "message": message}).encode("utf-8")

    req = request.Request(
        settings.WHATSAPP_API_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(settings.WHATSAPP_ACCESS_TOKEN),
        },
    )

    with request.urlopen(req, timeout=15) as response:
        status_code = response.getcode()
        if status_code < 200 or status_code >= 300:
            raise RuntimeError("WhatsApp API error: HTTP {}".format(status_code))
