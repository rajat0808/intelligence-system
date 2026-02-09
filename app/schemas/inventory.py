from datetime import date
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class InventoryBase(BaseModel):
    store_id: int
    product_id: int
    quantity: int
    cost_price: float = Field(
        validation_alias=AliasChoices("item_mrp", "cost_price"),
        serialization_alias="item_mrp",
    )
    current_price: float
    lifecycle_start_date: date

    model_config = ConfigDict(populate_by_name=True)


class InventoryCreate(InventoryBase):
    pass


class InventoryRead(InventoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExcelIngestRequest(BaseModel):
    path: str
    sheets: Optional[List[str]] = None
    dry_run: bool = False
