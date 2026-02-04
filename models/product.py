from sqlalchemy import Column, Integer, String, ForeignKey, Float, UniqueConstraint, Index
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # Identifiers
    style_code = Column(String, nullable=False)
    barcode = Column(String, nullable=False)

    # Product details
    article_name = Column(String, nullable=False)
    category = Column(String, nullable=False)

    # NEW FIELDS
    supplier_name = Column(String, nullable=False)
    mrp = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("store_id", "style_code", "barcode"),
        Index("idx_style", "style_code"),
        Index("idx_barcode", "barcode"),
    )
