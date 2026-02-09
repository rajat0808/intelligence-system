from datetime import date

from sqlalchemy import text

from app.core.aging_rules import classify_status_with_default
from app.core.danger_rules import calculate_age_in_days, danger_level
from app.database.engine import engine


def store_danger_summary():
    sql = text(
        """
        SELECT
            i.store_id,
            i.quantity,
            i.cost_price,
            p.mrp,
            i.lifecycle_start_date,
            p.category
        FROM inventory i
        LEFT JOIN products p ON p.id = i.product_id
        """
    )

    today = date.today()
    danger_summary = {}
    aging_summary = {}

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    for row in rows:
        store_id = row["store_id"]
        unit_price = row.get("mrp")
        if unit_price is None or unit_price <= 0:
            unit_price = row.get("cost_price") or 0.0
        capital = row["quantity"] * unit_price
        level = danger_level(row["lifecycle_start_date"])

        if level is not None:
            if store_id not in danger_summary:
                danger_summary[store_id] = {
                    "store_id": store_id,
                    "EARLY": 0.0,
                    "HIGH": 0.0,
                    "CRITICAL": 0.0,
                    "total_danger_capital": 0.0,
                }

            danger_summary[store_id][level] += capital
            danger_summary[store_id]["total_danger_capital"] += capital

        age_days = calculate_age_in_days(row["lifecycle_start_date"])
        if age_days is None:
            continue

        aging_status = classify_status_with_default(row["category"], age_days)

        if store_id not in aging_summary:
            aging_summary[store_id] = {
                "store_id": store_id,
                "HEALTHY": 0.0,
                "TRANSFER": 0.0,
                "RR_TT": 0.0,
                "VERY_DANGER": 0.0,
                "total_aging_capital": 0.0,
            }

        aging_summary[store_id][aging_status] += capital
        aging_summary[store_id]["total_aging_capital"] += capital

    return {
        "date": today,
        "store_count": len(danger_summary),
        "results": list(danger_summary.values()),
        "aging_results": list(aging_summary.values()),
    }
