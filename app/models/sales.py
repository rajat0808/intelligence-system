from sqlalchemy import Column, Date, ForeignKey, Index, Integer

from app.database.base import Base


class Sales(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity_sold = Column(Integer, nullable=False)
    sale_date = Column(Date, nullable=False)

    __table_args__ = (
        Index("idx_sales_product_store_date", "product_id", "store_id", "sale_date"),
    )


__all__ = ["Sales"]
