from datetime import date

from sqlalchemy import text

from app.core.aging_rules import classify_status_with_default
from app.core.danger_rules import calculate_age_in_days, danger_level
from app.database.engine import engine

AGING_STATUS_ALIASES = {
    "healthy": "HEALTHY",
    "transfer": "TRANSFER",
    "rr_tt": "RR_TT",
    "rate_revised": "RR_TT",
    "rate_revision": "RR_TT",
    "very_danger": "VERY_DANGER",
    "verydanger": "VERY_DANGER",
}


def _normalize_status_value(value):
    if value is None:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    key = key.replace("-", "_").replace(" ", "_")
    while "__" in key:
        key = key.replace("__", "_")
    key = key.strip("_")
    return AGING_STATUS_ALIASES.get(key)


def _normalize_status_filters(status_filters):
    if not status_filters:
        return set()
    raw_values = status_filters.split(",") if isinstance(status_filters, str) else status_filters
    normalized = set()
    for entry in raw_values:
        normalized_value = _normalize_status_value(entry)
        if normalized_value:
            normalized.add(normalized_value)
    return normalized


def _compute_status_counts(store_ids, aging_summary):
    counts = {"HEALTHY": 0, "TRANSFER": 0, "RR_TT": 0, "VERY_DANGER": 0}
    for store_id in store_ids:
        aging = aging_summary.get(store_id)
        if not aging:
            continue
        if aging.get("HEALTHY", 0) > 0:
            counts["HEALTHY"] += 1
        if aging.get("TRANSFER", 0) > 0:
            counts["TRANSFER"] += 1
        if aging.get("RR_TT", 0) > 0:
            counts["RR_TT"] += 1
        if aging.get("VERY_DANGER", 0) > 0:
            counts["VERY_DANGER"] += 1
    return counts


def _filter_store_ids_by_status(store_ids, aging_summary, normalized_filters):
    if not normalized_filters:
        return set(store_ids)
    filtered = set()
    for store_id in store_ids:
        aging = aging_summary.get(store_id)
        if not aging:
            continue
        for status in normalized_filters:
            if aging.get(status, 0) > 0:
                filtered.add(store_id)
                break
    return filtered


def store_danger_summary(status_filters=None, store_query=None):
    # noinspection SqlNoDataSourceInspection
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
    normalized_filters = _normalize_status_filters(status_filters)
    query_text = str(store_query).strip().lower() if store_query else ""
    query_is_numeric = query_text.isdigit() if query_text else False

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

    all_store_ids = set(danger_summary.keys()) | set(aging_summary.keys())
    store_ids = set(all_store_ids)

    if query_text:
        if query_is_numeric:
            store_ids = {
                store_id
                for store_id in store_ids
                if str(store_id).strip().lower() == query_text
            }
        else:
            store_ids = {
                store_id
                for store_id in store_ids
                if query_text in str(store_id).strip().lower()
            }

    base_store_ids = set(store_ids)
    status_counts = _compute_status_counts(base_store_ids, aging_summary)
    filtered_store_ids = _filter_store_ids_by_status(base_store_ids, aging_summary, normalized_filters)

    return {
        "date": today,
        "store_count": len(filtered_store_ids),
        "store_count_total": len(all_store_ids),
        "store_count_query": len(base_store_ids),
        "status_counts": status_counts,
        "results": [
            danger_summary[store_id]
            for store_id in filtered_store_ids
            if store_id in danger_summary
        ],
        "aging_results": [
            aging_summary[store_id] for store_id in filtered_store_ids if store_id in aging_summary
        ],
    }


def inventory_by_status(status_filters=None, store_query=None, store_id=None, limit=200):
    normalized_filters = _normalize_status_filters(status_filters)
    if not normalized_filters and not store_query and store_id is None:
        return {
            "count": 0,
            "results": [],
            "limited": False,
            "total_count": 0,
            "total_qty": 0,
            "total_value": 0.0,
        }

    query_text = str(store_query).strip().lower() if store_query else ""
    query_is_numeric = query_text.isdigit() if query_text else False
    params = {"store_id": store_id}

    # noinspection SqlNoDataSourceInspection
    sql = text(
        """
        SELECT
            p.style_code,
            p.article_name,
            p.category,
            p.department_name,
            p.supplier_name,
            p.image_url,
            p.mrp,
            i.store_id,
            i.quantity,
            i.current_price,
            i.cost_price,
            i.lifecycle_start_date
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        WHERE (:store_id IS NULL OR i.store_id = :store_id)
        ORDER BY p.article_name, i.store_id
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()

    results = []
    seen = {}
    limited = False

    for row in rows:
        store_value = row.get("store_id")
        if query_text and store_id is None:
            store_text = str(store_value).strip().lower()
            if query_is_numeric:
                if store_text != query_text:
                    continue
            elif query_text not in store_text:
                continue

        age_days = calculate_age_in_days(row["lifecycle_start_date"])
        if age_days is None:
            continue

        aging_status = classify_status_with_default(row["category"], age_days)
        if normalized_filters and aging_status not in normalized_filters:
            continue

        key = (store_value, row.get("style_code"), aging_status)
        if key in seen:
            existing = seen[key]
            existing["quantity"] += row.get("quantity") or 0
            existing["age_days"] = max(existing["age_days"], age_days)
            existing["days"] = existing["age_days"]
            continue

        mrp_value = row.get("mrp")
        if mrp_value is None or mrp_value <= 0:
            mrp_value = row.get("current_price") or row.get("cost_price") or 0.0

        item = {
            "style_code": row.get("style_code"),
            "article_name": row.get("article_name"),
            "category": row.get("category"),
            "department_name": row.get("department_name"),
            "supplier_name": row.get("supplier_name"),
            "image_url": row.get("image_url"),
            "store_id": store_value,
            "quantity": row.get("quantity") or 0,
            "age_days": age_days,
            "days": age_days,
            "item_mrp": mrp_value,
            "aging_status": aging_status,
        }
        seen[key] = item
        if len(results) < limit:
            results.append(item)
        else:
            limited = True

    total_qty = 0
    total_value = 0.0
    for entry in seen.values():
        qty = entry.get("quantity") or 0
        mrp_value = entry.get("item_mrp") or 0.0
        total_qty += qty
        total_value += qty * mrp_value

    return {
        "count": len(results),
        "results": results,
        "limited": limited,
        "total_count": len(seen),
        "total_qty": total_qty,
        "total_value": total_value,
    }
