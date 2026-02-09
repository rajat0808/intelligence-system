from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Index, Integer, String, UniqueConstraint

from app.database.base import Base


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True)
    job_name = Column(String(80), nullable=False)
    run_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="running")
    attempt = Column(Integer, nullable=False, default=1)

    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True))
    last_heartbeat_at = Column(DateTime(timezone=True))
    next_retry_at = Column(DateTime(timezone=True))

    locked_by = Column(String(120))
    error_message = Column(String)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("job_name", "run_date", name="uq_job_logs_name_date"),
        Index("idx_job_logs_status_retry", "status", "next_retry_at"),
        Index("idx_job_logs_run_date", "run_date"),
    )


__all__ = ["JobLog"]
