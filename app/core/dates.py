from datetime import date, datetime


def normalize_date(value):
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
