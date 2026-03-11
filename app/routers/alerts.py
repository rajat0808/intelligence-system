from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.dependencies import require_auth
from app.services.alert_service import run_alerts
from app.services.report_service import (
    DEFAULT_REPORT_NAME,
    build_alerts_from_database,
    create_and_send_daily_alert_reports,
    generate_daily_alert_report,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])
settings = get_settings()


@router.post("/run")
def run_alerts_now(
    send_notifications: bool = Query(
        not settings.ALERT_PDF_ONLY,
        description="Send external notifications (WhatsApp + Telegram)",
    ),
    force_resend: bool = Query(
        False,
        description="Ignore cooldown/dedup and resend alerts for matching records.",
    ),
    generate_pdf_report: bool = Query(
        True,
        description="Generate daily alert PDFs (50 alerts each by default, set ALERT_PDF_MAX_PER_DAY=0 for no daily cap).",
    ),
    send_pdf_to_telegram: bool = Query(
        True,
        description="Send generated daily alert report PDFs to Telegram.",
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
            report = create_and_send_daily_alert_reports(
                send_to_telegram=send_pdf_to_telegram,
                expected_count=settings.ALERT_PDF_PRODUCTS_PER_FILE,
                max_reports_per_day=settings.ALERT_PDF_MAX_PER_DAY,
            )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "completed", "stats": stats, "report": report}


@router.post(
    "/report/run",
    summary="Generate daily alert report PDFs on demand",
)
def run_daily_alert_report(
    send_pdf_to_telegram: bool = Query(
        True,
        description="Send generated daily alert report PDFs to Telegram.",
    ),
    expected_count: int = Query(
        settings.ALERT_PDF_PRODUCTS_PER_FILE,
        description="Number of alerts per PDF file.",
        ge=1,
    ),
    max_reports_per_day: int = Query(
        settings.ALERT_PDF_MAX_PER_DAY,
        description="Daily cap on PDF reports (0 = unlimited).",
        ge=0,
    ),
    _auth=Depends(require_auth),
):
    try:
        report = create_and_send_daily_alert_reports(
            send_to_telegram=send_pdf_to_telegram,
            expected_count=expected_count,
            max_reports_per_day=max_reports_per_day,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "completed", "report": report}


@router.get(
    "/report/pdf",
    response_class=FileResponse,
    summary="Download daily alert report PDF",
)
def download_daily_alert_report_pdf(_auth=Depends(require_auth)):
    try:
        alerts = build_alerts_from_database(limit=settings.ALERT_PDF_PRODUCTS_PER_FILE)
        report_path = generate_daily_alert_report(
            alerts,
            output_path=DEFAULT_REPORT_NAME,
            expected_count=settings.ALERT_PDF_PRODUCTS_PER_FILE,
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
