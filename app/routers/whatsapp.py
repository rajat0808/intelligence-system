import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import SessionLocal
from app.dependencies import require_auth
from app.models.delivery_logs import DeliveryLog
from app.services.whatsapp_service import send_whatsapp, send_whatsapp_template

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
logger = logging.getLogger(__name__)
_SUCCESSFUL_DELIVERY_STATUSES = {"sent", "delivered", "read"}


class WhatsAppSendRequest(BaseModel):
    message: str
    phone: str
    image_url: Optional[str] = None


class WhatsAppTemplateSendRequest(BaseModel):
    phone: str
    department: str
    category: str
    supplier: str
    mrp: str
    branch_code: str
    image_url: Optional[str] = None
    template_name: str = "inventory_transfer_alert"
    language_code: str = "en"
    api_url: Optional[str] = None
    access_token: Optional[str] = None
    media_base_url: Optional[str] = None


def _parse_event_timestamp(value: Any):
    if value is None:
        return None
    try:
        timestamp_seconds = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    try:
        return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _build_failure_reason(status_payload):
    errors = status_payload.get("errors")
    if not isinstance(errors, list):
        return None

    messages = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        title = str(item.get("title") or "").strip()
        detail = str(item.get("message") or "").strip()
        summary = " - ".join(part for part in (title, detail) if part)
        if code and summary:
            messages.append("{}: {}".format(code, summary))
        elif summary:
            messages.append(summary)
        elif code:
            messages.append(code)

    if not messages:
        return None
    return "; ".join(messages)


def _extract_status_events(payload):
    if not isinstance(payload, dict):
        return []

    events = []
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return events

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue

        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue

            metadata = value.get("metadata")
            if isinstance(metadata, dict):
                phone_number_id = str(metadata.get("phone_number_id") or "").strip()
            else:
                phone_number_id = ""

            statuses = value.get("statuses")
            if not isinstance(statuses, list):
                continue

            for status_payload in statuses:
                if not isinstance(status_payload, dict):
                    continue

                status_value = str(status_payload.get("status") or "").strip().lower()
                if not status_value:
                    status_value = "unknown"

                recipient_id = str(status_payload.get("recipient_id") or "").strip()
                message_id = str(status_payload.get("id") or "").strip()
                event_timestamp = _parse_event_timestamp(status_payload.get("timestamp"))
                event_date = event_timestamp.date() if event_timestamp else date.today()
                failure_reason = (
                    _build_failure_reason(status_payload)
                    if status_value == "failed"
                    else None
                )

                events.append(
                    {
                        "alert_date": event_date,
                        "alert_type": "WHATSAPP:{}".format(
                            message_id or "UNKNOWN_MESSAGE"
                        ),
                        "category": status_value,
                        "recipient": recipient_id or "unknown",
                        "phone_number": recipient_id or "unknown",
                        "message": "WhatsApp status '{}' for message '{}'".format(
                            status_value, message_id or "unknown"
                        ),
                        "capital_value": 0.0,
                        "delivered": status_value in _SUCCESSFUL_DELIVERY_STATUSES,
                        "failure_reason": failure_reason,
                        "provider_message_id": message_id or None,
                        "webhook_status": status_value,
                        "webhook_timestamp": event_timestamp,
                        "metadata_phone_number_id": phone_number_id or None,
                        "raw_payload": json.dumps(
                            status_payload, separators=(",", ":"), sort_keys=True
                        ),
                    }
                )
    return events


def _persist_status_events(status_events, *, session_factory=SessionLocal):
    if not status_events:
        return {"stored": 0, "updated": 0}

    db = session_factory()
    stored = 0
    updated = 0
    try:
        for item in status_events:
            existing = db.execute(
                select(DeliveryLog)
                .where(
                    DeliveryLog.alert_date == item["alert_date"],
                    DeliveryLog.alert_type == item["alert_type"],
                    DeliveryLog.category == item["category"],
                    DeliveryLog.phone_number == item["phone_number"],
                )
                .limit(1)
            ).scalar_one_or_none()

            if existing is None:
                db.add(DeliveryLog(**item))
                stored += 1
                continue

            existing.recipient = item["recipient"]
            existing.message = item["message"]
            existing.capital_value = item["capital_value"]
            existing.delivered = item["delivered"]
            existing.failure_reason = item["failure_reason"]
            existing.provider_message_id = item["provider_message_id"]
            existing.webhook_status = item["webhook_status"]
            existing.webhook_timestamp = item["webhook_timestamp"]
            existing.metadata_phone_number_id = item["metadata_phone_number_id"]
            existing.raw_payload = item["raw_payload"]
            updated += 1

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to persist WhatsApp webhook status events")
        return {"stored": 0, "updated": 0}
    finally:
        db.close()

    return {"stored": stored, "updated": updated}


@router.get("/webhook")
@router.get("/webhook/")
def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    verify_token = str(get_settings().WHATSAPP_WEBHOOK_VERIFY_TOKEN or "").strip()
    if not verify_token:
        raise HTTPException(
            status_code=500, detail="WHATSAPP_WEBHOOK_VERIFY_TOKEN is not configured"
        )

    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")
    if hub_verify_token != verify_token:
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    if not hub_challenge:
        raise HTTPException(status_code=400, detail="Missing hub.challenge")

    return PlainTextResponse(content=hub_challenge, status_code=200)


@router.post("/webhook")
@router.post("/webhook/")
async def receive_webhook(request: Request):
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    webhook_object = payload.get("object") if isinstance(payload, dict) else None
    status_events = _extract_status_events(payload)
    persist_summary = _persist_status_events(status_events)
    return {
        "status": "received",
        "object": webhook_object,
        "status_events": len(status_events),
        "stored": persist_summary["stored"],
        "updated": persist_summary["updated"],
    }


@router.post("/send")
def send_message(payload: WhatsAppSendRequest, _auth=Depends(require_auth)):
    message = payload.message.strip()
    phone = payload.phone.strip()

    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")

    try:
        send_whatsapp(message, phone, image_url=payload.image_url)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent", "phone": phone}


@router.post("/send-template")
def send_template_message(payload: WhatsAppTemplateSendRequest, _auth=Depends(require_auth)):
    phone = payload.phone.strip()
    department = payload.department.strip()
    category = payload.category.strip()
    supplier = payload.supplier.strip()
    mrp = payload.mrp.strip()
    branch_code = payload.branch_code.strip()
    template_name = payload.template_name.strip()
    language_code = payload.language_code.strip()

    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not department:
        raise HTTPException(status_code=400, detail="department is required")
    if not category:
        raise HTTPException(status_code=400, detail="category is required")
    if not supplier:
        raise HTTPException(status_code=400, detail="supplier is required")
    if not mrp:
        raise HTTPException(status_code=400, detail="mrp is required")
    if not branch_code:
        raise HTTPException(status_code=400, detail="branch_code is required")
    if not template_name:
        raise HTTPException(status_code=400, detail="template_name is required")
    if not language_code:
        raise HTTPException(status_code=400, detail="language_code is required")

    try:
        send_whatsapp_template(
            phone=phone,
            department=department,
            category=category,
            supplier=supplier,
            mrp=mrp,
            branch_code=branch_code,
            image_url=payload.image_url,
            template_name=template_name,
            language_code=language_code,
            api_url=payload.api_url,
            access_token=payload.access_token,
            media_base_url=payload.media_base_url,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent", "phone": phone, "template_name": template_name}
