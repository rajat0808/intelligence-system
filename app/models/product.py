from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint

from app.database.base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    style_code = Column(String, nullable=False)
    barcode = Column(String, nullable=False)

    article_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    department_name = Column(String, nullable=False, default="")

    supplier_name = Column(String, nullable=False)
    image_url = Column(String)
    mrp = Column(Float, nullable=False)
    price = Column(Float, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_price_update = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("store_id", "style_code", name="uq_products_store_style"),
        Index("idx_style", "style_code"),
        Index("idx_barcode", "barcode"),
    )


__all__ = ["Product"]
