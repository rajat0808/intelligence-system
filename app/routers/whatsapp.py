from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import require_auth
from app.services.whatsapp_service import send_whatsapp, send_whatsapp_template

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


class WhatsAppSendRequest(BaseModel):
    message: str
    phone: str
    image_url: Optional[str] = None


class WhatsAppTemplateSendRequest(BaseModel):
    phone: str
    store_id: str
    category: str
    department: str
    transfer_to: str
    aging_system_rule: str
    image_url: Optional[str] = None
    template_name: str = "inventory_transfer_alert"
    language_code: str = "en"
    api_url: Optional[str] = None
    access_token: Optional[str] = None
    media_base_url: Optional[str] = None


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
    store_id = payload.store_id.strip()
    category = payload.category.strip()
    department = payload.department.strip()
    transfer_to = payload.transfer_to.strip()
    aging_system_rule = payload.aging_system_rule.strip()
    template_name = payload.template_name.strip()
    language_code = payload.language_code.strip()

    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not store_id:
        raise HTTPException(status_code=400, detail="store_id is required")
    if not category:
        raise HTTPException(status_code=400, detail="category is required")
    if not department:
        raise HTTPException(status_code=400, detail="department is required")
    if not transfer_to:
        raise HTTPException(status_code=400, detail="transfer_to is required")
    if not aging_system_rule:
        raise HTTPException(status_code=400, detail="aging_system_rule is required")
    if not template_name:
        raise HTTPException(status_code=400, detail="template_name is required")
    if not language_code:
        raise HTTPException(status_code=400, detail="language_code is required")

    try:
        send_whatsapp_template(
            phone=phone,
            store_id=store_id,
            category=category,
            department=department,
            transfer_to=transfer_to,
            aging_system_rule=aging_system_rule,
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
