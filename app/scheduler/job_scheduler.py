from __future__ import annotations

import logging
import os
import socket
import threading
import time as time_module
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.models import import_all_models
from app.models.job_log import JobLog

logger = logging.getLogger(__name__)

STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"


def ensure_scheduler_schema() -> None:
    import_all_models()
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()


def parse_time(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) < 2:
        raise ValueError("SCHEDULER_RUN_AFTER must be in HH:MM format")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _owner_id() -> str:
    return "{}:{}".format(socket.gethostname(), os.getpid())


def _schedule_now(timezone_mode: str) -> datetime:
    if timezone_mode.lower() == "utc":
        return datetime.now(timezone.utc)
    return datetime.now()


def _cutoff_datetime(now: datetime, run_after: time) -> datetime:
    return now.replace(
        hour=run_after.hour,
        minute=run_after.minute,
        second=run_after.second,
        microsecond=0,
    )


def _is_stale(last_heartbeat: Optional[datetime], now: datetime, stale_seconds: int) -> bool:
    if last_heartbeat is None:
        return True
    return now - last_heartbeat > timedelta(seconds=stale_seconds)


def _truncate_error(value: str, limit: int = 1000) -> str:
    if value is None:
        return ""
    text = str(value)
    return text[:limit]


def _acquire_job_run(
    *,
    job_name: str,
    run_date,
    owner: str,
    stale_seconds: int,
    max_retries: int,
) -> Optional[JobLog]:
    now = utc_now()
    db = SessionLocal()
    try:
        log = JobLog(
            job_name=job_name,
            run_date=run_date,
            status=STATUS_RUNNING,
            attempt=1,
            started_at=now,
            last_heartbeat_at=now,
            locked_by=owner,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    except IntegrityError:
        db.rollback()
        existing = db.execute(
            select(JobLog).where(
                JobLog.job_name == job_name,
                JobLog.run_date == run_date,
            )
        ).scalar_one()

        if existing.status == STATUS_SUCCESS:
            return None

        if existing.status == STATUS_RUNNING:
            if not _is_stale(existing.last_heartbeat_at, now, stale_seconds):
                return None

        if existing.status == STATUS_FAILED:
            if existing.attempt >= max_retries:
                return None
            if existing.next_retry_at and now < existing.next_retry_at:
                return None

        stmt = (
            update(JobLog)
            .where(
                JobLog.id == existing.id,
                JobLog.status == existing.status,
                JobLog.last_heartbeat_at == existing.last_heartbeat_at,
            )
            .values(
                status=STATUS_RUNNING,
                attempt=existing.attempt + 1,
                started_at=now,
                last_heartbeat_at=now,
                finished_at=None,
                locked_by=owner,
                error_message=None,
                next_retry_at=None,
                updated_at=now,
            )
        )
        result = db.execute(stmt)
        if result.rowcount != 1:
            db.rollback()
            return None
        db.commit()
        return db.get(JobLog, existing.id)
    finally:
        db.close()


def _mark_job_success(job_id: int) -> None:
    now = utc_now()
    db = SessionLocal()
    try:
        db.execute(
            update(JobLog)
            .where(JobLog.id == job_id)
            .values(
                status=STATUS_SUCCESS,
                finished_at=now,
                last_heartbeat_at=now,
                error_message=None,
                next_retry_at=None,
                updated_at=now,
            )
        )
        db.commit()
    finally:
        db.close()


def _mark_job_failure(job_id: int, attempt: int, error: Exception, retry_seconds: int, max_retries: int) -> None:
    now = utc_now()
    next_retry = None
    if attempt < max_retries:
        next_retry = now + timedelta(seconds=retry_seconds * max(1, attempt))
    db = SessionLocal()
    try:
        db.execute(
            update(JobLog)
            .where(JobLog.id == job_id)
            .values(
                status=STATUS_FAILED,
                finished_at=now,
                last_heartbeat_at=now,
                error_message=_truncate_error("{}: {}".format(type(error).__name__, error)),
                next_retry_at=next_retry,
                updated_at=now,
            )
        )
        db.commit()
    finally:
        db.close()


def _heartbeat(job_id: int) -> None:
    now = utc_now()
    db = SessionLocal()
    try:
        db.execute(
            update(JobLog)
            .where(JobLog.id == job_id)
            .values(last_heartbeat_at=now, updated_at=now)
        )
        db.commit()
    finally:
        db.close()


class HeartbeatThread:
    def __init__(self, job_id: int, interval_seconds: int) -> None:
        self._job_id = job_id
        self._interval = max(5, int(interval_seconds))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="job-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=self._interval + 1)
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            try:
                _heartbeat(self._job_id)
            except Exception:
                logger.exception("Heartbeat update failed for job %s", self._job_id)


@dataclass
class SchedulerConfig:
    job_name: str
    run_after_time: time
    poll_seconds: int
    heartbeat_seconds: int
    stale_seconds: int
    retry_seconds: int
    max_retries: int
    timezone_mode: str = "local"


class DailyJobScheduler:
    def __init__(self, *, config: SchedulerConfig, job_func: Callable[[], None]) -> None:
        self._config = config
        self._job_func = job_func
        self._stop_event = threading.Event()

    def run_once(self) -> bool:
        now = _schedule_now(self._config.timezone_mode)
        cutoff = _cutoff_datetime(now, self._config.run_after_time)
        if now < cutoff:
            return False

        run_date = now.date()
        owner = _owner_id()
        job_log = _acquire_job_run(
            job_name=self._config.job_name,
            run_date=run_date,
            owner=owner,
            stale_seconds=self._config.stale_seconds,
            max_retries=self._config.max_retries,
        )
        if job_log is None:
            return False

        heartbeat = HeartbeatThread(job_log.id, self._config.heartbeat_seconds)
        heartbeat.start()
        try:
            logger.info("Running job %s for %s (attempt %s)", job_log.job_name, run_date, job_log.attempt)
            self._job_func()
            _mark_job_success(job_log.id)
            logger.info("Job %s completed for %s", job_log.job_name, run_date)
            return True
        except Exception as exc:
            logger.exception("Job %s failed for %s", job_log.job_name, run_date)
            _mark_job_failure(
                job_log.id,
                attempt=job_log.attempt,
                error=exc,
                retry_seconds=self._config.retry_seconds,
                max_retries=self._config.max_retries,
            )
            return False
        finally:
            heartbeat.stop()

    def run_forever(self) -> None:
        poll_seconds = max(1, int(self._config.poll_seconds))
        logger.info("Scheduler started for job %s", self._config.job_name)
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Scheduler loop error.")
            self._stop_event.wait(poll_seconds)

    def stop(self) -> None:
        self._stop_event.set()


__all__ = [
    "DailyJobScheduler",
    "SchedulerConfig",
    "ensure_scheduler_schema",
    "parse_time",
]
