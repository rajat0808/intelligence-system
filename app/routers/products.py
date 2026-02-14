from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.models.product import Product
from app.schemas.product import ProductPriceOverride, ProductReadWithHistory
from app.services.product_service import (
    apply_price_update,
    calculate_days_active,
    load_price_history,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/{style_code}", response_model=ProductReadWithHistory)
def get_product(style_code: str, db: Session = Depends(get_db)):
    product = (
        db.execute(select(Product).where(Product.style_code == style_code))
        .scalars()
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    history = load_price_history(db, product.id)
    base = ProductReadWithHistory.model_validate(product).model_dump()
    base["days_active"] = calculate_days_active(product.created_at)
    base["price_history"] = history
    return ProductReadWithHistory(**base)


@router.post("/price", response_model=ProductReadWithHistory)
def upsert_product_price(
    payload: ProductPriceOverride,
    db: Session = Depends(get_db),
    _auth=Depends(require_auth),
):
    if payload.price < 0:
        raise HTTPException(status_code=400, detail="price must be non-negative.")

    product = (
        db.execute(select(Product).where(Product.style_code == payload.style_code))
        .scalars()
        .first()
    )
    if product:
        if payload.barcode is not None:
            product.barcode = payload.barcode
        if payload.article_name is not None:
            product.article_name = payload.article_name
        if payload.category is not None:
            product.category = payload.category
        if payload.department_name is not None:
            product.department_name = payload.department_name
        if payload.supplier_name is not None:
            product.supplier_name = payload.supplier_name
        if payload.mrp is not None:
            product.mrp = payload.mrp
        apply_price_update(db, product, payload.price)
    else:
        missing = []
        if payload.store_id is None:
            missing.append("store_id")
        if payload.barcode is None:
            missing.append("barcode")
        if payload.article_name is None:
            missing.append("article_name")
        if payload.category is None:
            missing.append("category")
        if payload.supplier_name is None:
            missing.append("supplier_name")
        if payload.mrp is None:
            missing.append("mrp")
        if missing:
            raise HTTPException(
                status_code=400,
                detail="Missing fields for new product: {}".format(", ".join(missing)),
            )
        product = Product(
            store_id=payload.store_id,
            style_code=payload.style_code,
            barcode=payload.barcode,
            article_name=payload.article_name,
            category=payload.category,
            department_name=payload.department_name or "",
            supplier_name=payload.supplier_name,
            mrp=payload.mrp,
            price=payload.price,
            last_price_update=datetime.now(timezone.utc),
        )
        db.add(product)

    db.commit()
    db.refresh(product)

    history = load_price_history(db, product.id)
    base = ProductReadWithHistory.model_validate(product).model_dump()
    base["days_active"] = calculate_days_active(product.created_at)
    base["price_history"] = history
    return ProductReadWithHistory(**base)


__all__ = ["router"]
