from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.database.engine import engine
from app.ml.predict import predict_risk
from app.schemas.ml import MLPredictRequest, MLPredictResponse
from app.services.ml_service import predict_and_log

router = APIRouter(prefix="/ml", tags=["ML"])


def _normalize_start_date(value):
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


@router.post("/predict", response_model=MLPredictResponse)
def predict(payload: MLPredictRequest):
    score = predict_and_log(
        category=payload.category,
        quantity=payload.quantity,
        cost_price=payload.item_mrp,
        lifecycle_start_date=payload.lifecycle_start_date,
        current_price=payload.current_price,
        mrp=payload.mrp,
        department_name=payload.department_name,
        supplier_name=payload.supplier_name,
        store_id=payload.store_id,
    )
    return MLPredictResponse(risk_score=score)


@router.get("/inventory")
def inventory_risk(
    store_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    min_risk: Optional[float] = Query(None),
    limit: int = Query(200),
):
    if min_risk is not None and (min_risk < 0 or min_risk > 1):
        raise HTTPException(status_code=400, detail="min_risk must be between 0 and 1")
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")

    category_value = None
    if category is not None:
        category_value = str(category).strip()
        if not category_value:
            category_value = None

    where_clauses = []
    params = {"limit": limit}

    if store_id is not None:
        where_clauses.append("i.store_id = :store_id")
        params["store_id"] = store_id
    if product_id is not None:
        where_clauses.append("i.product_id = :product_id")
        params["product_id"] = product_id
    if category_value:
        where_clauses.append("LOWER(p.category) = LOWER(:category)")
        params["category"] = category_value

    where_sql = ""
    if where_clauses:
        where_sql = " AND " + " AND ".join(where_clauses)

    sql = text(
        """
        SELECT
            i.store_id,
            i.product_id,
            i.quantity,
            i.cost_price,
            i.current_price,
            i.lifecycle_start_date,
            p.style_code,
            p.article_name,
            p.category,
            p.department_name,
            p.supplier_name,
            p.mrp
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        WHERE 1=1
        {where_sql}
        ORDER BY i.store_id, p.style_code
        LIMIT :limit
        """.format(where_sql=where_sql)
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()

    results = []
    for row in rows:
        start_date = _normalize_start_date(row["lifecycle_start_date"])
        item_mrp = row["mrp"]
        if item_mrp is None or item_mrp <= 0:
            item_mrp = row["cost_price"]
        mrp_value = row["mrp"]
        if mrp_value is None or mrp_value <= 0:
            mrp_value = item_mrp
        if start_date is None:
            risk = None
        else:
            risk = predict_risk(
                category=row["category"],
                quantity=row["quantity"],
                cost_price=item_mrp,
                lifecycle_start_date=start_date,
                current_price=row["current_price"],
                mrp=mrp_value,
                department_name=row["department_name"],
                supplier_name=row["supplier_name"],
                store_id=row["store_id"],
            )
        if min_risk is not None:
            if risk is None or risk < min_risk:
                continue
        results.append(
            {
                "store_id": row["store_id"],
                "product_id": row["product_id"],
                "style_code": row["style_code"],
                "article_name": row["article_name"],
                "category": row["category"],
                "department_name": row["department_name"],
                "supplier_name": row["supplier_name"],
                "mrp": mrp_value,
                "item_mrp": item_mrp,
                "quantity": row["quantity"],
                "lifecycle_start_date": row["lifecycle_start_date"],
                "risk_score": risk,
            }
        )

    return {"count": len(results), "results": results}
