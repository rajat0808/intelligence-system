from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery_logs import DeliveryLog


def alert_already_sent(
    db,
    alert_date,
    alert_type,
    category,
    phone,
):
    stmt = (
        select(DeliveryLog.id)
        .where(
            DeliveryLog.alert_date == alert_date,
            DeliveryLog.alert_type == alert_type,
            DeliveryLog.category == category,
            DeliveryLog.phone_number == phone,
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None
