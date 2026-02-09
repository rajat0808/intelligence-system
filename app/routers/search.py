from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from app.core.dashboard_auth import require_login_api
from app.core.aging_rules import classify_status_with_default
from app.core.danger_rules import calculate_age_in_days, danger_level
from app.database.engine import engine

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/inventory")
def search_inventory(
    request: Request,
    query=Query(None, description="Style code or article name"),
    department=Query(None, description="Filter by department name (comma-separated)"),
    store_id=Query(None, description="Filter by store ID"),
    danger=Query(None, description="EARLY | HIGH | CRITICAL"),
    alert_only=Query(False, description="Show only items that are in danger"),
):
    require_login_api(request)
    if query is not None:
        query = str(query).strip()
        if not query:
            query = None
        elif len(query) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters.")

    departments = []
    if department:
        for entry in str(department).split(","):
            entry = entry.strip()
            if entry:
                departments.append(entry)

    if not query and not departments:
        raise HTTPException(
            status_code=400,
            detail="Provide a search query or department filter.",
        )

    if store_id is not None:
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="store_id must be an integer.")

    alert_only = str(alert_only).strip().lower() in ("1", "true", "yes", "y")

    department_clause = ""
    params = {
        "q": "%{}%".format(query) if query else None,
        "store_id": store_id,
    }

    if departments:
        department_filters = []
        for idx, entry in enumerate(departments):
            key = "dept_{}".format(idx)
            department_filters.append("LOWER(p.department_name) = :{}".format(key))
            params[key] = entry.lower()
        department_clause = "AND ({})".format(" OR ".join(department_filters))

    sql = text(
        """
        SELECT
            p.style_code,
            p.article_name,
            p.category,
            p.department_name,
            p.supplier_name,
            p.mrp,
            i.store_id,
            i.quantity,
            i.current_price,
            i.lifecycle_start_date
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        WHERE
            (
                :q IS NULL
                OR LOWER(p.style_code) LIKE LOWER(:q)
                OR LOWER(p.article_name) LIKE LOWER(:q)
            )
            AND (:store_id IS NULL OR i.store_id = :store_id)
            {department_clause}
        ORDER BY
            p.article_name,
            i.store_id
        """.format(department_clause=department_clause)
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()

    results = []

    for row in rows:
        item = dict(row)
        item["category_name"] = item.get("category")

        age_days = calculate_age_in_days(item["lifecycle_start_date"])
        item["age_days"] = age_days
        item["stock_days"] = age_days
        item["days"] = age_days

        if age_days is None:
            item["aging_status"] = None
        else:
            item["aging_status"] = classify_status_with_default(item["category"], age_days)

        level = danger_level(item["lifecycle_start_date"])
        item["danger_level"] = level
        mrp_value = item.get("mrp")
        if mrp_value is None or mrp_value <= 0:
            mrp_value = item.get("current_price")
        item["item_mrp"] = mrp_value
        item["item_price"] = mrp_value

        if alert_only and level is None:
            continue

        if danger and level != danger:
            continue

        results.append(item)

    return {"count": len(results), "results": results}
