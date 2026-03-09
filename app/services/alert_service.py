import json
from datetime import date, timedelta

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
from app.services.notification_service import send_inventory_alert
from app.services.whatsapp_service import send_whatsapp

settings = get_settings()
_STATUS_RANK = {
    "HEALTHY": 0,
    "TRANSFER": 1,
    "RR_TT": 2,
    "VERY_DANGER": 3,
}
_ALERT_PRIORITY = {
    "RULE-CRITICAL": 300,
    "RULE-HIGH": 250,
    "ML-RISK-CRITICAL": 200,
    "ML-RISK-HIGH": 150,
    "ML-RISK-ELEVATED": 100,
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


def build_transfer_hint(style_code, style_store_index, current_store_id):
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

    store_id_value = str(best_store.get("store_id")).strip()
    store_name_value = str(best_store.get("store_name") or "").strip()
    if store_id_value == "1" or store_name_value.casefold() == "store 1":
        store_label = "HEAD OFFICE"
    else:
        store_label = "Store {}".format(best_store["store_id"])

    if best_store.get("store_name") and store_label != "HEAD OFFICE":
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
    store_id_value = str(store_id).strip() if store_id is not None else ""
    store_name_value = str(store_name or "").strip()
    if store_id_value == "1" or store_name_value.casefold() == "store 1":
        label = "HEAD OFFICE"
    else:
        label = str(store_id)

    if store_name and label != "HEAD OFFICE":
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
            Alert.delivered.is_(True),
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _find_existing_alert(db, alert_date, alert_type, category, phone):
    stmt = (
        select(Alert)
        .where(
            Alert.alert_date == alert_date,
            Alert.alert_type == alert_type,
            Alert.category == category,
            Alert.phone_number == phone,
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _recent_alert_sent(db, *, since_date, alert_type, category, phone):
    stmt = (
        select(Alert.id)
        .where(
            Alert.alert_date >= since_date,
            Alert.alert_type == alert_type,
            Alert.category == category,
            Alert.phone_number == phone,
            Alert.delivered.is_(True),
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _resolve_ml_reason(ml_risk):
    base_threshold = max(0.0, min(1.0, float(settings.ML_ALERT_THRESHOLD)))
    high_threshold = max(base_threshold, min(1.0, float(settings.ML_ALERT_HIGH_THRESHOLD)))
    critical_threshold = max(high_threshold, min(1.0, float(settings.ML_ALERT_CRITICAL_THRESHOLD)))

    if ml_risk >= critical_threshold:
        return "ML-RISK-CRITICAL"
    if ml_risk >= high_threshold:
        return "ML-RISK-HIGH"
    if ml_risk >= base_threshold:
        return "ML-RISK-ELEVATED"
    return None


def _resolve_alert_reason(danger, ml_risk):
    if danger == "CRITICAL":
        return "RULE-CRITICAL"
    if danger == "HIGH":
        return "RULE-HIGH"
    return _resolve_ml_reason(ml_risk)


def _is_low_signal_ml_alert(alert_reason, danger, capital_value):
    if alert_reason is None:
        return True
    if danger in ("HIGH", "CRITICAL"):
        return False
    if not alert_reason.startswith("ML-RISK"):
        return False
    return capital_value < max(0.0, float(settings.ALERT_MIN_CAPITAL_VALUE))


def _alert_sort_key(alert_reason, age_days, capital_value, ml_risk):
    return (
        _ALERT_PRIORITY.get(alert_reason or "", 0),
        age_days,
        capital_value,
        ml_risk,
    )


def run_alerts(*, send_notifications=True, always_send=None):
    db = SessionLocal()
    today = date.today()
    send_notifications_enabled = bool(send_notifications) and not bool(settings.ALERT_PDF_ONLY)
    always_send_enabled = (
        bool(always_send) if always_send is not None else bool(settings.ALERT_ALWAYS_SEND)
    )

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
        .order_by(Inventory.lifecycle_start_date.asc(), Inventory.quantity.desc())
    ).all()
    style_store_index = _build_style_store_index(inventories, today)

    sent_alerts = set()
    recipient_alert_counts = {}
    cooldown_days = max(0, int(settings.ALERT_COOLDOWN_DAYS))
    cooldown_start = today - timedelta(days=max(0, cooldown_days - 1))
    max_per_run = max(1, int(settings.ALERT_MAX_PER_RECIPIENT_PER_RUN))
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

        alert_candidates = []

        for row in inventories:
            inv = row.Inventory
            category = row.category
            mrp = row.mrp
            style_code = (row.style_code or "").strip()
            department_name = (row.department_name or "").strip() or "Unspecified"
            image_url = row.image_url
            store_label = _format_store_label(inv.store_id, row.store_name, row.store_city)
            transfer_hint = build_transfer_hint(style_code, style_store_index, inv.store_id)

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

            capital_value = inv.quantity * unit_price
            alert_reason = _resolve_alert_reason(danger, ml_risk)
            if _is_low_signal_ml_alert(alert_reason, danger, capital_value):
                continue

            alert_candidates.append(
                {
                    "row": row,
                    "category": category,
                    "style_code": style_code,
                    "department_name": department_name,
                    "image_url": image_url,
                    "store_label": store_label,
                    "transfer_hint": transfer_hint,
                    "status": status,
                    "age": age,
                    "ml_risk": ml_risk,
                    "capital_value": capital_value,
                    "alert_reason": alert_reason,
                }
            )

        alert_candidates.sort(
            key=lambda item: _alert_sort_key(
                item["alert_reason"],
                item["age"],
                item["capital_value"],
                item["ml_risk"],
            ),
            reverse=True,
        )

        for candidate in alert_candidates:
            row = candidate["row"]
            inv = row.Inventory
            category = candidate["category"]
            alert_reason = candidate["alert_reason"]
            ml_risk = candidate["ml_risk"]
            capital_value = candidate["capital_value"]

            for recipient_name, phone in recipients:
                if not phone:
                    continue

                if recipient_alert_counts.get(phone, 0) >= max_per_run:
                    continue

                alert_key = (today, alert_reason, category, phone)
                if alert_key in sent_alerts:
                    continue

                if not always_send_enabled:
                    if _recent_alert_sent(
                        db,
                        since_date=cooldown_start,
                        alert_type=alert_reason,
                        category=category,
                        phone=phone,
                    ):
                        sent_alerts.add(alert_key)
                        continue

                existing_alert = _find_existing_alert(
                    db,
                    alert_date=today,
                    alert_type=alert_reason,
                    category=category,
                    phone=phone,
                )

                if not always_send_enabled:
                    if alert_already_sent(
                        db,
                        alert_date=today,
                        alert_type=alert_reason,
                        category=category,
                        phone=phone,
                    ):
                        sent_alerts.add(alert_key)
                        continue

                capital_locked = "{:,.0f}".format(capital_value)
                message = (
                    "\u26A0 INVENTORY ALERT ({})\n\n"
                    "Category Name: {}\n"
                    "Department Name: {}\n"
                    "Style Code: {}\n"
                    "Store: {}\n"
                    "Stock Days: {}\n"
                    "Age: {} days\n"
                    "Aging Status: {}\n"
                    "Capital Locked: \u20B9{}\n"
                    "{}"
                ).format(
                    today,
                    category,
                    candidate["department_name"],
                    candidate["style_code"] or "N/A",
                    candidate["store_label"],
                    candidate["age"],
                    candidate["age"],
                    candidate["status"],
                    capital_locked,
                    candidate["transfer_hint"],
                )

                delivered = False
                failure_reason = None
                if send_notifications_enabled:
                    channel_failures = []
                    whatsapp_delivered = False
                    if settings.WHATSAPP_NOTIFICATIONS_ENABLED:
                        try:
                            send_whatsapp(message, phone, image_url=candidate["image_url"])
                            whatsapp_delivered = True
                        except (RuntimeError, ValueError) as exc:
                            channel_failures.append("WhatsApp: {}".format(exc))

                    telegram_image = candidate["image_url"] or settings.TELEGRAM_FALLBACK_IMAGE
                    telegram_results = send_inventory_alert(
                        message,
                        channels=["telegram"],
                        image_url=telegram_image,
                    )
                    telegram_delivered = telegram_results.get("telegram", False)
                    if not telegram_delivered:
                        channel_failures.append("Telegram delivery failed")

                    delivered = whatsapp_delivered or telegram_delivered
                    if channel_failures:
                        failure_reason = " | ".join(channel_failures)

                if existing_alert is None:
                    db.add(
                        Alert(
                            alert_date=today,
                            alert_type=alert_reason,
                            category=category,
                            store_id=inv.store_id,
                            recipient=recipient_name,
                            phone_number=phone,
                            message=message,
                            capital_value=capital_value,
                            delivered=delivered,
                            failure_reason=failure_reason,
                        )
                    )
                else:
                    existing_alert.store_id = inv.store_id
                    existing_alert.recipient = recipient_name
                    existing_alert.message = message
                    existing_alert.capital_value = capital_value
                    existing_alert.delivered = delivered
                    existing_alert.failure_reason = failure_reason

                recipient_alert_counts[phone] = recipient_alert_counts.get(phone, 0) + 1
                stats["alerts"] += 1
                sent_alerts.add(alert_key)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()

    return stats
