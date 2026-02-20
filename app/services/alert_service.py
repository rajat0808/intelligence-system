import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.core.aging_rules import classify_status_with_default
from app.core.danger_rules import danger_level
from app.core.decision_engine import evaluate_inventory
from app.database import SessionLocal
from app.models.alert import Alert
from app.models.daily_snapshot import DailySnapshot
from app.models.inventory import Inventory
from app.models.product import Product
from app.services.ml_service import predict_and_log
from app.services.whatsapp_service import send_whatsapp

settings = get_settings()


def alert_already_sent(db, alert_date, alert_type, category, phone):
    stmt = (
        select(Alert.id)
        .where(
            Alert.alert_date == alert_date,
            Alert.alert_type == alert_type,
            Alert.category == category,
            Alert.phone_number == phone,
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def run_alerts(*, send_notifications=True):
    db = SessionLocal()
    today = date.today()

    inventories = db.execute(
        select(Inventory, Product.category, Product.mrp).join(
            Product,
            Product.id == Inventory.product_id,
        )
    ).all()

    sent_alerts = set()
    recipients = [
        ("Founder", settings.FOUNDER_PHONE),
        ("Co-Founder", settings.CO_FOUNDER_PHONE),
    ]

    stats = {"snapshots": 0, "alerts": 0}

    try:
        existing_snapshots = {
            (snapshot.store_id, snapshot.product_id): snapshot
            for snapshot in db.execute(
                select(DailySnapshot).where(DailySnapshot.snapshot_date == today)
            ).scalars()
        }

        for row in inventories:
            inv = row.Inventory
            category = row.category
            mrp = row.mrp

            age = (today - inv.lifecycle_start_date).days
            status = classify_status_with_default(category, age)
            danger = danger_level(inv.lifecycle_start_date)
            unit_price = mrp
            if unit_price is None or unit_price <= 0:
                unit_price = inv.cost_price
            mrp_value = mrp
            if mrp_value is None or mrp_value <= 0:
                mrp_value = unit_price

            decision = evaluate_inventory(
                category=category,
                age_days=age,
                demand_band="M",
                danger_level=danger,
            )

            snapshot_key = (inv.store_id, inv.product_id)
            snapshot = existing_snapshots.get(snapshot_key)
            if snapshot is None:
                snapshot = DailySnapshot(
                    snapshot_date=today,
                    store_id=inv.store_id,
                    product_id=inv.product_id,
                )
                existing_snapshots[snapshot_key] = snapshot
                db.add(snapshot)

            snapshot.age_days = age
            snapshot.status = status
            snapshot.demand_band = "M"
            snapshot.quantity = inv.quantity
            snapshot.cost_price = unit_price
            snapshot.mrp = mrp_value
            snapshot.stock_value = inv.quantity * unit_price
            snapshot.decision = json.dumps(decision)
            stats["snapshots"] += 1

            ml_risk = predict_and_log(
                db=db,
                category=category,
                quantity=inv.quantity,
                cost_price=unit_price,
                lifecycle_start_date=inv.lifecycle_start_date,
                current_price=inv.current_price,
                mrp=mrp_value,
                store_id=inv.store_id,
                product_id=inv.product_id,
            )

            alert_reason = None
            if danger in ("HIGH", "CRITICAL"):
                alert_reason = f"RULE-{danger}"
            elif ml_risk >= settings.ML_ALERT_THRESHOLD:
                alert_reason = "ML-RISK-{:.2f}".format(ml_risk)

            if alert_reason:
                for recipient_name, phone in recipients:
                    if not phone:
                        continue
                    alert_key = (today, alert_reason, category, phone)
                    if alert_key in sent_alerts:
                        continue

                    if alert_already_sent(
                        db,
                        alert_date=today,
                        alert_type=alert_reason,
                        category=category,
                        phone=phone,
                    ):
                        sent_alerts.add(alert_key)
                        continue

                    capital_locked = "{:,.0f}".format(inv.quantity * unit_price)
                    message = (
                        "\u26A0 INVENTORY ALERT ({})\n\n"
                        "Recipient: {}\n"
                        "Reason: {}\n"
                        "Category: {}\n"
                        "Store ID: {}\n"
                        "Age: {} days\n"
                        "ML Risk Score: {:.2f}\n"
                        "Capital Locked: \u20B9{}"
                    ).format(
                        today,
                        recipient_name,
                        alert_reason,
                        category,
                        inv.store_id,
                        age,
                        ml_risk,
                        capital_locked,
                    )

                    delivered = False
                    failure_reason = None
                    if send_notifications:
                        try:
                            send_whatsapp(message, phone)
                            delivered = True
                        except (RuntimeError, ValueError) as exc:
                            failure_reason = str(exc)

                    db.add(
                        Alert(
                            alert_date=today,
                            alert_type=alert_reason,
                            category=category,
                            store_id=inv.store_id,
                            recipient=recipient_name,
                            phone_number=phone,
                            message=message,
                            capital_value=inv.quantity * unit_price,
                            delivered=delivered,
                            failure_reason=failure_reason,
                        )
                    )
                    stats["alerts"] += 1
                    sent_alerts.add(alert_key)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

    return stats
