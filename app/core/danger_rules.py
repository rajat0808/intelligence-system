from datetime import date, datetime


def calculate_age_in_days(lifecycle_start_date):
    if lifecycle_start_date is None:
        return None
    if isinstance(lifecycle_start_date, datetime):
        lifecycle_start_date = lifecycle_start_date.date()
    if isinstance(lifecycle_start_date, str):
        value_text = lifecycle_start_date.strip()
        if not value_text:
            return None
        try:
            lifecycle_start_date = date.fromisoformat(value_text)
        except ValueError:
            return None
    if not isinstance(lifecycle_start_date, date):
        return None
    return (date.today() - lifecycle_start_date).days


def danger_level(lifecycle_start_date):
    age = calculate_age_in_days(lifecycle_start_date)
    if age is None:
        return None
    if age >= 365:
        return "CRITICAL"
    if age >= 250:
        return "HIGH"
    if age >= 180:
        return "EARLY"
    return None
