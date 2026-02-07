from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.whatsapp_service import send_whatsapp


router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


class WhatsAppSendRequest(BaseModel):
    message: str
    phone: str


@router.post("/send")
def send_message(payload: WhatsAppSendRequest):
    message = payload.message.strip()
    phone = payload.phone.strip()

    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")

    try:
        send_whatsapp(message, phone)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent", "phone": phone}
