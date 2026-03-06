from datetime import date
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class MLPredictRequest(BaseModel):
    category: str = Field(min_length=1, max_length=120)
    quantity: float = Field(gt=0, le=1_000_000)
    item_mrp: float = Field(
        gt=0,
        le=1_000_000_000,
        validation_alias=AliasChoices("item_mrp", "cost_price"),
    )
    lifecycle_start_date: date
    current_price: Optional[float] = Field(default=None, gt=0, le=1_000_000_000)
    mrp: Optional[float] = Field(default=None, gt=0, le=1_000_000_000)
    department_name: Optional[str] = Field(default=None, max_length=150)
    supplier_name: Optional[str] = Field(default=None, max_length=150)
    store_id: Optional[int] = Field(default=None, ge=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("category", "department_name", "supplier_name", mode="before")
    @classmethod
    def _normalize_text(cls, value):
        if value is None:
            return value
        text = str(value).strip()
        return text if text else None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value):
        if value is None:
            raise ValueError("category is required")
        return value


class MLPredictResponse(BaseModel):
    risk_score: float


class MLStatusResponse(BaseModel):
    mode: str
    model_available: bool
    model_loaded: bool
    load_error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
