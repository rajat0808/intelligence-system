from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text
from datetime import date
from app.database import engine
from app.intelligence.danger_rules import danger_level

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/inventory")
def search_inventory(
    query=Query(None, description="Style code or article name"),
    store_id=Query(None, description="Filter by store ID"),
    danger=Query(
        None,
        description="EARLY | HIGH | CRITICAL"
    ),
    alert_only=Query(
        False,
        description="Show only items that are in danger (alert-visible)"
    ),
):
    if query is None or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters.")

    if store_id is not None:
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="store_id must be an integer.")

    alert_only = str(alert_only).strip().lower() in ("1", "true", "yes", "y")

    sql = text("""
        SELECT
            p.style_code,
            p.article_name,
            p.category,
            p.supplier_name,
            p.mrp,
            i.store_id,
            i.quantity,
            i.cost_price,
            i.current_price,
            i.lifecycle_start_date
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        WHERE
            (
                LOWER(p.style_code) LIKE LOWER(:q)
                OR LOWER(p.article_name) LIKE LOWER(:q)
            )
            AND (:store_id IS NULL OR i.store_id = :store_id)
        ORDER BY
            p.article_name,
            i.store_id
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "q": "%{}%".format(query),
                "store_id": store_id
            }
        ).mappings().all()

    today = date.today()
    results = []

    for row in rows:
        item = dict(row)

        # =========================
        # STOCK AGE (DAYS)
        # =========================
        age_days = (today - item["lifecycle_start_date"]).days
        item["age_days"] = age_days

        # =========================
        # DANGER LEVEL (DERIVED)
        # =========================
        level = danger_level(item["lifecycle_start_date"])
        item["danger_level"] = level

        # =========================
        # ALERT-VISIBLE FILTER
        # =========================
        if alert_only and level is None:
            continue

        # =========================
        # DANGER FILTER
        # =========================
        if danger and level != danger:
            continue

        results.append(item)

    return {
        "count": len(results),
        "results": results
    }
