def _normalize_category(category):
    category_value = str(category or "").strip().lower()
    if not category_value:
        return ""

    normalized = category_value.replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    compact = normalized.replace(" ", "")

    if "dress material" in normalized or "dress material" in compact:
        return "dress material"
    if "lehenga" in normalized:
        return "lehenga"
    if "saree" in normalized:
        return "saree"
    if "dress" in normalized:
        return "dress"
    return normalized


def classify_status(category, age):
    category = _normalize_category(category)

    if category == "dress":
        if age <= 90:
            return "HEALTHY"
        if age <= 180:
            return "TRANSFER"
        if age <= 365:
            return "RR_TT"
        return "VERY_DANGER"

    if category == "dress material":
        if age <= 90:
            return "HEALTHY"
        if age <= 180:
            return "TRANSFER"
        if age <= 365:
            return "RR_TT"
        return "VERY_DANGER"

    if category == "lehenga":
        if age <= 250:
            return "HEALTHY"
        if age <= 365:
            return "TRANSFER"
        return "VERY_DANGER"

    if category == "saree":
        if age <= 365:
            return "HEALTHY"
        return "VERY_DANGER"

    raise ValueError("Unknown category: {}".format(category))


def classify_status_with_default(category, age, default_category="dress"):
    try:
        return classify_status(category, age)
    except ValueError:
        return classify_status(default_category, age)
