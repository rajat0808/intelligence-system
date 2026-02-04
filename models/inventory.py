from sqlalchemy import Column, Integer, Float, Date, ForeignKey, Index
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)

    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Stock & pricing
    quantity = Column(Integer, nullable=False)
    cost_price = Column(Float, nullable=False)      # already correct
    current_price = Column(Float, nullable=False)   # selling price

    lifecycle_start_date = Column(Date, nullable=False)

    __table_args__ = (
        Index("idx_store_product", "store_id", "product_id"),
    )
