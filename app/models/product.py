from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, UniqueConstraint

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
    mrp = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("store_id", "style_code", "barcode"),
        Index("idx_style", "style_code"),
        Index("idx_barcode", "barcode"),
    )


__all__ = ["Product"]
