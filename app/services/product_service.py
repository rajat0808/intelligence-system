from datetime import datetime, timezone
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory
from app.models.product import Product


def apply_price_update(
    db: Session,
    product: Product,
    new_price: float | None,
    *,
    changed_at: datetime | None = None,
) -> datetime | None:
    if new_price is None:
        return None

    new_price = float(new_price)
    old_price = float(product.price) if product.price is not None else None
    if old_price is not None and old_price == new_price:
        return None

    if changed_at is None:
        changed_at = datetime.now(timezone.utc)
    elif changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    else:
        changed_at = changed_at.astimezone(timezone.utc)

    if product.id is not None:
        db.add(
            PriceHistory(
                product_id=product.id,
                old_price=old_price if old_price is not None else 0.0,
                new_price=new_price,
                changed_at=changed_at,
            )
        )
    product.price = new_price
    product.last_price_update = changed_at
    return changed_at


def calculate_days_active(created_at: datetime | None) -> int | None:
    if created_at is None:
        return None
    created_date = created_at.date()
    return (datetime.now(timezone.utc).date() - created_date).days


def load_price_history(db: Session, product_id: int) -> list[PriceHistory]:
    history = (
        db.execute(
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.changed_at.desc())
        )
        .scalars()
        .all()
    )
    return cast(list[PriceHistory], list(history))
