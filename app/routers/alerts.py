from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import require_auth
from app.services.alert_service import run_alerts
from app.services.report_service import (
    ALERTS_PER_PDF,
    DEFAULT_REPORT_NAME,
    build_alerts_from_database,
    create_and_send_daily_alert_report,
    generate_daily_alert_report,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/run")
def run_alerts_now(
    send_notifications: bool = Query(
        True,
        description="Send external notifications (WhatsApp + Telegram)",
    ),
    force_resend: bool = Query(
        False,
        description="Ignore cooldown/dedup and resend alerts for matching records.",
    ),
    generate_pdf_report: bool = Query(
        True,
        description="Generate daily_alert_report.pdf with 50 alerts.",
    ),
    send_pdf_to_telegram: bool = Query(
        True,
        description="Send daily_alert_report.pdf to Telegram.",
    ),
    _auth=Depends(require_auth),
):
    try:
        stats = run_alerts(
            send_notifications=send_notifications,
            always_send=force_resend,
        )
        report = None
        if generate_pdf_report:
            report = create_and_send_daily_alert_report(
                send_to_telegram=send_pdf_to_telegram,
            )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "completed", "stats": stats, "report": report}


@router.get(
    "/report/pdf",
    response_class=FileResponse,
    summary="Download daily alert report PDF",
)
def download_daily_alert_report_pdf(_auth=Depends(require_auth)):
    try:
        alerts = build_alerts_from_database(limit=ALERTS_PER_PDF)
        report_path = generate_daily_alert_report(
            alerts,
            output_path=DEFAULT_REPORT_NAME,
            expected_count=ALERTS_PER_PDF,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=DEFAULT_REPORT_NAME,
    )
