from __future__ import annotations

from datetime import date, datetime
import math


def _normalize_text(value) -> str:
    if value is None:
        return "unknown"
    value_text = str(value).strip().lower()
    return value_text if value_text else "unknown"


def _to_float(value, default=0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, str):
        value_text = value.strip()
        if not value_text:
            return float(default)
        try:
            return float(value_text)
        except ValueError:
            return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value, default=0) -> int:
    if value is None:
        return int(default)
    if isinstance(value, bool):
        return int(default)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return int(default)
    if isinstance(value, str):
        value_text = value.strip()
        if not value_text:
            return int(default)
        try:
            return int(value_text)
        except ValueError:
            try:
                numeric = float(value_text)
            except ValueError:
                return int(default)
            if numeric.is_integer():
                return int(numeric)
            return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value_text = value.strip()
        if not value_text:
            return None
        try:
            return date.fromisoformat(value_text)
        except ValueError:
            return None
    return None


def compute_age_days(as_of_date, lifecycle_start_date, age_days=None) -> int:
    if age_days is not None:
        return max(0, _to_int(age_days))
    start_date = _to_date(lifecycle_start_date)
    as_of = _to_date(as_of_date) or date.today()
    if start_date is None:
        return 0
    return max(0, (as_of - start_date).days)


def build_feature_dict(
    *,
    category,
    quantity,
    cost_price,
    lifecycle_start_date=None,
    as_of_date=None,
    age_days=None,
    current_price=None,
    mrp=None,
    department_name=None,
    supplier_name=None,
    store_id=None,
):
    as_of = _to_date(as_of_date) or date.today()
    age_value = compute_age_days(as_of, lifecycle_start_date, age_days=age_days)

    quantity_value = max(0.0, _to_float(quantity, default=0.0))
    cost_value = max(0.0, _to_float(cost_price, default=0.0))
    current_value = _to_float(current_price, default=cost_value)
    if current_value <= 0.0:
        current_value = cost_value
    mrp_value = _to_float(mrp, default=current_value)
    if mrp_value <= 0.0:
        mrp_value = current_value

    stock_value = quantity_value * cost_value
    price_ratio = current_value / cost_value if cost_value > 0 else 1.0
    mrp_ratio = mrp_value / cost_value if cost_value > 0 else 1.0
    discount_ratio = current_value / mrp_value if mrp_value > 0 else 1.0

    store_text = "store_unknown"
    if store_id is not None:
        store_text = "store_{}".format(str(store_id).strip() or "unknown")

    return {
        "category": _normalize_text(category),
        "department": _normalize_text(department_name),
        "supplier": _normalize_text(supplier_name),
        "store": store_text,
        "age_days": float(age_value),
        "quantity": float(quantity_value),
        "cost_price": float(cost_value),
        "current_price": float(current_value),
        "mrp": float(mrp_value),
        "stock_value": float(stock_value),
        "price_ratio": float(price_ratio),
        "mrp_ratio": float(mrp_ratio),
        "discount_ratio": float(discount_ratio),
        "log_quantity": float(math.log1p(quantity_value)),
        "log_cost_price": float(math.log1p(cost_value)),
        "log_stock_value": float(math.log1p(stock_value)),
        "log_age_days": float(math.log1p(age_value)),
    }
