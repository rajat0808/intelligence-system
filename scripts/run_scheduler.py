import argparse
import logging

from app.config import get_settings
from app.core.logging import setup_logging
from app.scheduler.job_scheduler import DailyJobScheduler, SchedulerConfig, ensure_scheduler_schema, parse_time
from app.services.alert_service import run_alerts

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Run the alert scheduler.")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run the alert workflow once and exit.",
    )
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()
    settings = get_settings()

    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled by SCHEDULER_ENABLED.")
        return

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

    if args.run_once:
        scheduler.run_once()
        return

    scheduler.run_forever()


if __name__ == "__main__":
    main()
