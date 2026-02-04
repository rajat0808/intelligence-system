from datetime import date


_VALUE_RISK_CAP = 0.2
_VALUE_SCALE = 1000000.0

_CATEGORY_RISK = {
    "dress": 0.03,
    "dress material": 0.02,
    "lehenga": 0.05,
    "saree": 0.03,
}


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


def predict_risk(category, quantity, cost_price, lifecycle_start_date):
    """Heuristic ML placeholder: returns a 0..1 risk score."""
    age_days = max(0, (date.today() - lifecycle_start_date).days)
    age_component = _age_risk(age_days)

    stock_value = max(0.0, float(quantity) * float(cost_price))
    value_component = min(stock_value / _VALUE_SCALE, 1.0) * _VALUE_RISK_CAP

    category_component = _CATEGORY_RISK.get(str(category).lower(), 0.0)

    return _clamp(age_component + value_component + category_component)
