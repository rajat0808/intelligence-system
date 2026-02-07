from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from app.ml.predict import predict_risk


router = APIRouter(prefix="/ml", tags=["ML"])


class MLPredictRequest(BaseModel):
    category: str
    quantity: float
    cost_price: float
    lifecycle_start_date: date


class MLPredictResponse(BaseModel):
    risk_score: float


@router.post("/predict", response_model=MLPredictResponse)
def predict(payload: MLPredictRequest):
    score = predict_risk(
        category=payload.category,
        quantity=payload.quantity,
        cost_price=payload.cost_price,
        lifecycle_start_date=payload.lifecycle_start_date,
    )
    return MLPredictResponse(risk_score=score)
