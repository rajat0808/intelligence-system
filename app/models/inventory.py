from sqlalchemy import Column, Date, Float, ForeignKey, Index, Integer

from app.database.base import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)

    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    cost_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)

    lifecycle_start_date = Column(Date, nullable=False)

    __table_args__ = (
        Index("idx_store_product", "store_id", "product_id"),
    )


__all__ = ["Inventory"]
