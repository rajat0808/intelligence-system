from datetime import date
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class InventoryBase(BaseModel):
    store_id: int = Field(ge=1)
    product_id: int = Field(ge=1)
    quantity: int = Field(ge=0, le=1_000_000)
    cost_price: float = Field(
        gt=0,
        le=1_000_000_000,
        validation_alias=AliasChoices("item_mrp", "cost_price"),
        serialization_alias="item_mrp",
    )
    current_price: float = Field(gt=0, le=1_000_000_000)
    lifecycle_start_date: date

    model_config = ConfigDict(populate_by_name=True)


class InventoryCreate(InventoryBase):
    pass


class InventoryRead(InventoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExcelIngestRequest(BaseModel):
    path: str = Field(min_length=3, max_length=400)
    sheets: Optional[List[str]] = None
    dry_run: bool = False

    @field_validator("path", mode="before")
    @classmethod
    def _normalize_path(cls, value):
        return str(value).strip() if value is not None else value
