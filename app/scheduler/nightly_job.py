from app.config import get_settings
from app.core.logging import setup_logging
from app.scheduler.job_scheduler import DailyJobScheduler, SchedulerConfig, ensure_scheduler_schema, parse_time
from app.services.alert_service import run_alerts

if __name__ == "__main__":
    setup_logging()
    settings = get_settings()
    ensure_scheduler_schema()
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
    scheduler = DailyJobScheduler(config=config, job_func=run_alerts)
    scheduler.run_once()
