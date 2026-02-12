from datetime import date
import logging
import math

from app.ml.features import build_feature_dict
from app.ml.model_io import load_model, model_available


_VALUE_RISK_CAP = 0.2
_VALUE_SCALE = 1000000.0

_CATEGORY_RISK = {
    "dress": 0.03,
    "dress material": 0.02,
    "lehenga": 0.05,
    "saree": 0.03,
}

_MODEL = None
_MODEL_METADATA = None
_MODEL_LOAD_ERROR = None

_LOGGER = logging.getLogger(__name__)


def _clamp(value, low=0.0, high=1.0):
    if value < low:
        return low
    if value > high:
        return high
    return value


def _age_risk(age_days):
    if age_days < 90:
        return 0.15
    if age_days < 180:
        return 0.3
    if age_days < 250:
        return 0.55
    if age_days < 365:
        return 0.75
    return 0.9


def _heuristic_risk(category, quantity, cost_price, lifecycle_start_date):
    age_days = max(0, (date.today() - lifecycle_start_date).days)
    age_component = _age_risk(age_days)

    stock_value = max(0.0, float(quantity) * float(cost_price))
    value_component = min(stock_value / _VALUE_SCALE, 1.0) * _VALUE_RISK_CAP

    category_component = _CATEGORY_RISK.get(str(category).lower(), 0.0)

    return _clamp(age_component + value_component + category_component)


def _load_model_once():
    global _MODEL, _MODEL_METADATA, _MODEL_LOAD_ERROR
    if _MODEL is not None or _MODEL_LOAD_ERROR is not None:
        return _MODEL
    try:
        model, metadata = load_model()
    # noinspection PyBroadException
    except Exception as exc:
        _MODEL_LOAD_ERROR = exc
        _LOGGER.warning("Failed to load ML model: %s", exc)
        return None
    if model is None:
        _MODEL_LOAD_ERROR = "missing"
        return None
    _MODEL = model
    _MODEL_METADATA = metadata
    return _MODEL


def model_is_available():
    return model_available()


def predict_risk(
    category,
    quantity,
    cost_price,
    lifecycle_start_date,
    *,
    as_of_date=None,
    age_days=None,
    current_price=None,
    mrp=None,
    department_name=None,
    supplier_name=None,
    store_id=None,
):
    """Return a 0..1 risk score using the trained model when available."""
    features = build_feature_dict(
        category=category,
        quantity=quantity,
        cost_price=cost_price,
        lifecycle_start_date=lifecycle_start_date,
        as_of_date=as_of_date,
        age_days=age_days,
        current_price=current_price,
        mrp=mrp,
        department_name=department_name,
        supplier_name=supplier_name,
        store_id=store_id,
    )

    model = _load_model_once()
    if model is not None:
        if hasattr(model, "predict_proba"):
            prob = model.predict_proba([features])[0][1]
        elif hasattr(model, "decision_function"):
            score = model.decision_function([features])[0]
            prob = 1.0 / (1.0 + math.exp(-float(score)))
        else:
            prob = model.predict([features])[0]
        return _clamp(float(prob))

    return _heuristic_risk(category, quantity, cost_price, lifecycle_start_date)


__all__ = ["predict_risk", "model_is_available"]
