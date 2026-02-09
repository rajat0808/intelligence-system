def evaluate_inventory(category, age_days, demand_band, danger_level):
    actions = []
    explanation = []
    context = {
        "category": category,
        "age_days": age_days,
    }

    if danger_level == "CRITICAL":
        actions += ["RATE_REVISION", "STIPEND_INCENTIVE"]
        explanation.append("Critical aging risk")

    if demand_band == "H":
        explanation.append("High demand - conservative action")

    return {
        "status": "ACTION_REQUIRED" if actions else "HEALTHY",
        "eligible_actions": actions,
        "lifecycle_action": "RESET" if "RATE_REVISION" in actions else "CONTINUE",
        "explanation": explanation,
        "context": context,
    }
