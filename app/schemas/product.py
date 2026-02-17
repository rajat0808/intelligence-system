from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    store_id: int
    style_code: str
    barcode: str
    article_name: str
    category: str
    department_name: Optional[str] = ""
    supplier_name: str
    image_url: Optional[str] = None
    mrp: float


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryRead(BaseModel):
    old_price: float
    new_price: float
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductPriceOverride(BaseModel):
    style_code: str
    price: float
    store_id: Optional[int] = None
    barcode: Optional[str] = None
    article_name: Optional[str] = None
    category: Optional[str] = None
    department_name: Optional[str] = None
    supplier_name: Optional[str] = None
    image_url: Optional[str] = None
    mrp: Optional[float] = None


class ProductReadWithHistory(ProductRead):
    price: float
    created_at: datetime
    last_price_update: Optional[datetime] = None
    days_active: Optional[int] = None
    price_history: List[PriceHistoryRead] = Field(default_factory=list)
