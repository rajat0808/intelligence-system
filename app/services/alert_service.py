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
from app.models.stores import Store
from app.services.ml_service import predict_and_log
from app.services.whatsapp_service import send_whatsapp

settings = get_settings()
_STATUS_RANK = {
    "HEALTHY": 0,
    "TRANSFER": 1,
    "RR_TT": 2,
    "VERY_DANGER": 3,
}


def _build_style_store_index(inventories, today):
    style_store_index = {}
    for row in inventories:
        inv = row.Inventory
        style_code = (row.style_code or "").strip()
        if not style_code:
            continue

        age_days = (today - inv.lifecycle_start_date).days
        status = classify_status_with_default(row.category, age_days)
        style_store_index.setdefault(style_code, []).append(
            {
                "store_id": inv.store_id,
                "store_name": row.store_name,
                "store_city": row.store_city,
                "age_days": age_days,
                "status": status,
                "quantity": inv.quantity,
            }
        )
    return style_store_index


def _build_transfer_hint(style_code, style_store_index, current_store_id):
    if not style_code:
        return "Transfer Hint: Style code unavailable for peer-store comparison."

    peers = [
        item for item in style_store_index.get(style_code, []) if item["store_id"] != current_store_id
    ]
    if not peers:
        return "Transfer Hint: No peer-store data for this style yet."

    best_store = min(
        peers,
        key=lambda item: (
            _STATUS_RANK.get(item["status"], 99),
            item["age_days"],
            item["quantity"],
        ),
    )

    store_label = "Store {}".format(best_store["store_id"])
    if best_store.get("store_name"):
        store_label += " ({})".format(best_store["store_name"])
    if best_store.get("store_city"):
        store_label += ", {}".format(best_store["store_city"])

    if best_store["status"] == "HEALTHY":
        return (
            "Transfer Hint: Style {} is doing well at {} "
            "(status {}, age {} days, qty {})."
        ).format(
            style_code,
            store_label,
            best_store["status"],
            best_store["age_days"],
            best_store["quantity"],
        )

    return (
        "Transfer Hint: No strong healthy signal found. Best available target is {} "
        "(status {}, age {} days, qty {})."
    ).format(
        store_label,
        best_store["status"],
        best_store["age_days"],
        best_store["quantity"],
    )


def _format_store_label(store_id, store_name, store_city):
    label = str(store_id)
    if store_name:
        label = "{} ({})".format(label, store_name)
    if store_city:
        label = "{}, {}".format(label, store_city)
    return label


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
        select(
            Inventory,
            Product.category.label("category"),
            Product.mrp.label("mrp"),
            Product.style_code.label("style_code"),
            Product.department_name.label("department_name"),
            Product.image_url.label("image_url"),
            Store.name.label("store_name"),
            Store.city.label("store_city"),
        )
        .join(
            Product,
            Product.id == Inventory.product_id,
        )
        .outerjoin(Store, Store.id == Inventory.store_id)
    ).all()
    style_store_index = _build_style_store_index(inventories, today)

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
            style_code = (row.style_code or "").strip()
            department_name = (row.department_name or "").strip() or "Unspecified"
            image_url = row.image_url
            store_label = _format_store_label(inv.store_id, row.store_name, row.store_city)
            transfer_hint = _build_transfer_hint(style_code, style_store_index, inv.store_id)

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
                        "Category Name: {}\n"
                        "Department Name: {}\n"
                        "Style Code: {}\n"
                        "Store: {}\n"
                        "Stock Days: {}\n"
                        "Age: {} days\n"
                        "ML Risk Score: {:.2f}\n"
                        "Capital Locked: \u20B9{}\n"
                        "{}"
                    ).format(
                        today,
                        recipient_name,
                        alert_reason,
                        category,
                        department_name,
                        style_code or "N/A",
                        store_label,
                        age,
                        age,
                        ml_risk,
                        capital_locked,
                        transfer_hint,
                    )

                    delivered = False
                    failure_reason = None
                    if send_notifications:
                        try:
                            send_whatsapp(message, phone, image_url=image_url)
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
