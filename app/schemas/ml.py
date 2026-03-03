from datetime import date
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MLPredictRequest(BaseModel):
    category: str
    quantity: float
    item_mrp: float = Field(
        validation_alias=AliasChoices("item_mrp", "cost_price"),
    )
    lifecycle_start_date: date
    current_price: Optional[float] = None
    mrp: Optional[float] = None
    department_name: Optional[str] = None
    supplier_name: Optional[str] = None
    store_id: Optional[int] = None

    model_config = ConfigDict(populate_by_name=True)


class MLPredictResponse(BaseModel):
    risk_score: float


class MLStatusResponse(BaseModel):
    mode: str
    model_available: bool
    model_loaded: bool
    load_error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
