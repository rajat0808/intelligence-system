import json

from app.ml.predict import predict_risk
from app.models.risk_log import RiskLog


def predict_and_log(
    *,
    db=None,
    category,
    quantity,
    cost_price,
    lifecycle_start_date,
    current_price=None,
    mrp=None,
    department_name=None,
    supplier_name=None,
    store_id=None,
    product_id=None,
):
    score = predict_risk(
        category=category,
        quantity=quantity,
        cost_price=cost_price,
        lifecycle_start_date=lifecycle_start_date,
        current_price=current_price,
        mrp=mrp,
        department_name=department_name,
        supplier_name=supplier_name,
        store_id=store_id,
    )

    if db is not None:
        context = {
            "category": category,
            "quantity": quantity,
            "item_mrp": cost_price,
            "current_price": current_price,
            "mrp": mrp,
            "department_name": department_name,
            "supplier_name": supplier_name,
            "store_id": store_id,
            "product_id": product_id,
        }
        db.add(
            RiskLog(
                store_id=store_id,
                product_id=product_id,
                risk_score=float(score),
                context=json.dumps(context, default=str),
            )
        )
    return float(score)
