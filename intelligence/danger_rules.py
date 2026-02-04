from datetime import date


def calculate_age_in_days(start_date):
    return (date.today() - start_date).days


def danger_level(start_date):
    age = calculate_age_in_days(start_date)

    if age >= 365:
        return "CRITICAL"
    if age >= 250:
        return "HIGH"
    if age >= 180:
        return "EARLY"
    return None
