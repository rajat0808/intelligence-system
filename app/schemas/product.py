from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    store_id: int
    style_code: str
    barcode: str
    article_name: str
    category: str
    department_name: Optional[str] = ""
    supplier_name: str
    mrp: float


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
