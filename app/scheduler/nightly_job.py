import logging

from app.config import get_settings
from app.core.logging import setup_logging
from app.scheduler.job_scheduler import DailyJobScheduler, SchedulerConfig, ensure_scheduler_schema, parse_time
from app.services.alert_service import run_alerts
from app.services.report_service import create_and_send_daily_alert_reports

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    setup_logging()
    settings = get_settings()
    ensure_scheduler_schema()

    def run_alerts_with_report():
        stats = run_alerts(send_notifications=not settings.ALERT_PDF_ONLY)
        try:
            create_and_send_daily_alert_reports(
                send_to_telegram=True,
                expected_count=settings.ALERT_PDF_PRODUCTS_PER_FILE,
                max_reports_per_day=settings.ALERT_PDF_MAX_PER_DAY,
            )
        except ValueError as exc:
            logger.warning("Daily PDF report skipped: %s", exc)
        except Exception:
            logger.exception("Daily PDF report generation failed.")
        return stats

    config = SchedulerConfig(
        job_name="daily-intelligence",
        run_after_time=parse_time(settings.SCHEDULER_RUN_AFTER),
        poll_seconds=settings.SCHEDULER_POLL_SECONDS,
        heartbeat_seconds=settings.SCHEDULER_HEARTBEAT_SECONDS,
        stale_seconds=settings.SCHEDULER_STALE_SECONDS,
        retry_seconds=settings.SCHEDULER_RETRY_SECONDS,
        max_retries=settings.SCHEDULER_MAX_RETRIES,
        timezone_mode=settings.SCHEDULER_TZ,
    )
    scheduler = DailyJobScheduler(config=config, job_func=run_alerts_with_report)
    scheduler.run_once()
