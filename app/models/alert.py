from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Index, Integer, String

from app.database.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    alert_date = Column(Date, nullable=False)
    alert_type = Column(String, nullable=False)
    category = Column(String, nullable=False)

    store_id = Column(Integer)
    recipient = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    message = Column(String, nullable=False)

    capital_value = Column(Float, nullable=False)
    delivered = Column(Boolean, nullable=False)
    failure_reason = Column(String)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_alert_dedup", "alert_date", "alert_type", "category", "phone_number", unique=True),
    )


__all__ = ["Alert"]
