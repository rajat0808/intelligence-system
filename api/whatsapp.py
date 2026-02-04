from fastapi import APIRouter

router = APIRouter(prefix="/whatsapp")


@router.post("/send")
def send_message(payload):
    return {"status": "stub", "message": payload["message"]}
