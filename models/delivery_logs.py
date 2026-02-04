from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Float, Index
from app.database import Base


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True)
    alert_date = Column(Date, nullable=False)
    alert_type = Column(String, nullable=False)
    category = Column(String, nullable=False)

    recipient = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    message = Column(String, nullable=False)

    capital_value = Column(Float, nullable=False)
    delivered = Column(Boolean, nullable=False)
    failure_reason = Column(String)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_delivery_dedup", "alert_date", "alert_type", "category", "phone_number", unique=True),
    )
