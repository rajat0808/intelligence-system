from __future__ import annotations

import logging
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_SCHEDULED_JOB_EXCEPTIONS = (OSError, RuntimeError, ValueError)


def _parse_time(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) < 2:
        raise ValueError("SCHEDULER_TIME must be in HH:MM format")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)


def _next_daily_run(run_time: time, *, tz: Optional[timezone] = None) -> datetime:
    now = datetime.now(tz=tz)
    candidate = now.replace(
        hour=run_time.hour,
        minute=run_time.minute,
        second=run_time.second,
        microsecond=0,
    )
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


@dataclass
class ScheduledJob:
    name: str
    run_time: time
    func: Callable[[], None]
    jitter_seconds: int = 0
    run_in_thread: bool = True
    next_run: Optional[datetime] = None


class Scheduler:
    def __init__(self, *, timezone_mode: str = "local", poll_seconds: int = 1):
        self._jobs: list[ScheduledJob] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._poll_seconds = max(1, int(poll_seconds))
        self._tz = timezone.utc if timezone_mode.lower() == "utc" else None

    def add_daily_job(
        self,
        name: str,
        run_time: str,
        func: Callable[[], None],
        *,
        jitter_seconds: int = 0,
        run_in_thread: bool = True,
    ) -> None:
        run_at = _parse_time(run_time)
        job = ScheduledJob(
            name=name,
            run_time=run_at,
            func=func,
            jitter_seconds=max(0, int(jitter_seconds)),
            run_in_thread=run_in_thread,
        )
        job.next_run = self._schedule_next(job)
        with self._lock:
            self._jobs.append(job)

    def _schedule_next(self, job: ScheduledJob) -> datetime:
        run_at = _next_daily_run(job.run_time, tz=self._tz)
        if job.jitter_seconds:
            run_at += timedelta(seconds=secrets.randbelow(job.jitter_seconds + 1))
        return run_at

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Scheduler started with %d job(s).", len(self._jobs))

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=self._poll_seconds + 1)
        self._thread = None
        logger.info("Scheduler stopped.")

    def run_pending(self) -> None:
        now = datetime.now(tz=self._tz)
        with self._lock:
            jobs = list(self._jobs)
        for job in jobs:
            if job.next_run and now >= job.next_run:
                self._run_job(job)
                job.next_run = self._schedule_next(job)

    def _run_job(self, job: ScheduledJob) -> None:
        logger.info("Running scheduled job: %s", job.name)
        if job.run_in_thread:
            threading.Thread(
                target=self._safe_run,
                args=(job,),
                name=f"job-{job.name}",
                daemon=True,
            ).start()
        else:
            self._safe_run(job)

    @staticmethod
    def _safe_run(job: ScheduledJob) -> None:
        try:
            job.func()
        except _SCHEDULED_JOB_EXCEPTIONS:
            logger.exception("Scheduled job failed: %s", job.name)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.run_pending()
            self._stop_event.wait(self._poll_seconds)
