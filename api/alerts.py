from fastapi import APIRouter, HTTPException

from app.scheduler.nightly_job import nightly_run


router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/run")
def run_alerts():
    try:
        nightly_run()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "completed"}
