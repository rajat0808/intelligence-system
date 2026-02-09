from sqlalchemy import Column, Date, Float, ForeignKey, Index, Integer, String

from app.database.base import Base


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)

    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    age_days = Column(Integer, nullable=False)

    quantity = Column(Integer, nullable=False)
    cost_price = Column(Float, nullable=False)
    mrp = Column(Float, nullable=False)

    stock_value = Column(Float, nullable=False)

    status = Column(String, nullable=False)
    demand_band = Column(String(1), nullable=False)
    decision = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_snapshot_psd", "product_id", "store_id", "snapshot_date"),
    )


__all__ = ["DailySnapshot"]
