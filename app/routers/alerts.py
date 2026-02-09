from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import require_auth
from app.services.alert_service import run_alerts

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/run")
def run_alerts_now(
    send_notifications: bool = Query(True, description="Send WhatsApp notifications"),
    _auth=Depends(require_auth),
):
    try:
        stats = run_alerts(send_notifications=send_notifications)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "completed", "stats": stats}
