from datetime import date, datetime


def _normalize_start_date(start_date):
    if start_date is None:
        return None
    if isinstance(start_date, datetime):
        return start_date.date()
    if isinstance(start_date, date):
        return start_date
    if isinstance(start_date, str):
        value = start_date.strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
    return None


def calculate_age_in_days(start_date):
    normalized = _normalize_start_date(start_date)
    if normalized is None:
        return None
    return (date.today() - normalized).days


def danger_level(start_date):
    age = calculate_age_in_days(start_date)
    if age is None:
        return None

    if age >= 365:
        return "CRITICAL"
    if age >= 250:
        return "HIGH"
    if age >= 180:
        return "EARLY"
    return None
