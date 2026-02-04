import json
from datetime import date
from sqlalchemy import text

from app.database import SessionLocal
from app.config import get_settings
from app.models.daily_snapshot import DailySnapshot
from app.models.delivery_logs import DeliveryLog

from app.intelligence import aging_rules, danger_rules
from app.intelligence.decision_engine import evaluate_inventory

from app.services.whatsapp_service import send_whatsapp
from app.services.alert_engine import alert_already_sent

# ML IMPORT
from app.ml.predict import predict_risk

settings = get_settings()

RECIPIENTS = [
    ("Founder", settings.FOUNDER_PHONE),
    ("Co-Founder", settings.CO_FOUNDER_PHONE),
]


def nightly_run():
    db = SessionLocal()
    today = date.today()

    inventories = db.execute(text("""
        SELECT i.*, p.category
        FROM inventory i
        JOIN products p ON p.id = i.product_id
    """)).fetchall()

    try:
        for inv in inventories:
            # =========================
            # BASIC DERIVED VALUES
            # =========================
            age = (today - inv.lifecycle_start_date).days
            status = aging_rules.classify_status(inv.category, age)
            danger = danger_rules.danger_level(inv.lifecycle_start_date)

            # =========================
            # DECISION ENGINE (RULES)
            # =========================
            decision = evaluate_inventory(
                category=inv.category,
                age_days=age,
                demand_band="M",
                danger_level=danger
            )

            # =========================
            # SAVE DAILY SNAPSHOT
            # =========================
            db.add(
                DailySnapshot(
                    snapshot_date=today,
                    store_id=inv.store_id,
                    product_id=inv.product_id,
                    age_days=age,
                    status=status,
                    demand_band="M",
                    quantity=inv.quantity,
                    stock_value=inv.quantity * inv.cost_price,
                    decision=json.dumps(decision)
                )
            )

            # =========================
            # ML RISK PREDICTION
            # =========================
            ml_risk = predict_risk(
                category=inv.category,
                quantity=inv.quantity,
                cost_price=inv.cost_price,
                lifecycle_start_date=inv.lifecycle_start_date
            )

            # =========================
            # ALERT DECISION (RULE + ML)
            # =========================
            alert_reason = None

            if danger in ("HIGH", "CRITICAL"):
                alert_reason = "RULE-{}".format(danger)

            elif ml_risk >= settings.ML_ALERT_THRESHOLD:
                alert_reason = "ML-RISK-{:.2f}".format(ml_risk)

            # =========================
            # SEND WHATSAPP ALERT
            # =========================
            if alert_reason:
                for recipient_name, phone in RECIPIENTS:

                    if alert_already_sent(
                        db,
                        alert_date=today,
                        alert_type=alert_reason,
                        category=inv.category,
                        phone=phone
                    ):
                        continue

                    capital_locked = "{:,.0f}".format(inv.quantity * inv.cost_price)
                    message = (
                        u"\u26A0 INVENTORY ALERT ({})\n\n"
                        "Recipient: {}\n"
                        "Reason: {}\n"
                        "Category: {}\n"
                        "Store ID: {}\n"
                        "Age: {} days\n"
                        "ML Risk Score: {:.2f}\n"
                        u"Capital Locked: \u20B9{}"
                    ).format(
                        today,
                        recipient_name,
                        alert_reason,
                        inv.category,
                        inv.store_id,
                        age,
                        ml_risk,
                        capital_locked
                    )

                    try:
                        send_whatsapp(message, phone)

                        db.add(
                            DeliveryLog(
                                alert_date=today,
                                alert_type=alert_reason,
                                category=inv.category,
                                recipient=recipient_name,
                                phone_number=phone,
                                message=message,
                                capital_value=inv.quantity * inv.cost_price,
                                delivered=True
                            )
                        )

                    except Exception as e:
                        db.add(
                            DeliveryLog(
                                alert_date=today,
                                alert_type=alert_reason,
                                category=inv.category,
                                recipient=recipient_name,
                                phone_number=phone,
                                message=message,
                                capital_value=inv.quantity * inv.cost_price,
                                delivered=False,
                                failure_reason=str(e)
                            )
                        )

        db.commit()

        print(" Nightly job completed (Rules + ML alerts sent)")

    except Exception as e:
        db.rollback()
        print(" Nightly job failed:", e)

    finally:
        db.close()
