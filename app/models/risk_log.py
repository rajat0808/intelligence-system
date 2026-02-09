from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class RiskLog(Base):
    __tablename__ = "risk_logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    store_id = Column(Integer)
    product_id = Column(Integer)
    risk_score = Column(Float, nullable=False)

    model_version = Column(String)
    context = Column(String)


__all__ = ["RiskLog"]
