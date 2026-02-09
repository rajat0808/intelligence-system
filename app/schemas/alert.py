from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    id: int
    alert_date: date
    alert_type: str
    category: str
    store_id: Optional[int]
    recipient: str
    phone_number: str
    message: str
    capital_value: float
    delivered: bool
    failure_reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
