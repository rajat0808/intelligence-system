def evaluate_inventory(category, age_days, demand_band, danger_level):
    actions = []
    explanation = []
    context = {
        "category": category,
        "age_days": age_days,
    }

    demand_value = str(demand_band or "").strip().upper() or "M"

    if danger_level == "CRITICAL":
        actions += ["RATE_REVISION", "STIPEND_INCENTIVE", "PRIORITY_TRANSFER"]
        explanation.append("Critical aging risk")
    elif danger_level == "HIGH":
        actions.append("PRIORITY_TRANSFER")
        explanation.append("High aging risk")

    if age_days is not None and age_days >= 180 and demand_value in ("L", "M"):
        actions.append("TRANSFER_REVIEW")
        explanation.append("Aging crossed transfer review threshold")

    if demand_value == "H":
        explanation.append("High demand - conservative action")
        if "TRANSFER_REVIEW" in actions:
            actions.remove("TRANSFER_REVIEW")

    return {
        "status": "ACTION_REQUIRED" if actions else "HEALTHY",
        "eligible_actions": sorted(set(actions)),
        "lifecycle_action": "RESET" if "RATE_REVISION" in actions else "CONTINUE",
        "explanation": explanation,
        "context": context,
    }
