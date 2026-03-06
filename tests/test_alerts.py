import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.alert import Alert
from app.services.alert_service import (
    _is_low_signal_ml_alert,
    _recent_alert_sent,
    _resolve_alert_reason,
    alert_already_sent,
    build_transfer_hint,
)


class AlertServiceTest(unittest.TestCase):
    def test_alert_dedup(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine)
        db = None
        try:
            db = session_factory()
            db.add(
                Alert(
                    alert_date=date.today(),
                    alert_type="RULE-HIGH",
                    category="dress",
                    store_id=101,
                    recipient="Founder",
                    phone_number="12345",
                    message="Test",
                    capital_value=1000.0,
                    delivered=True,
                )
            )
            db.commit()

            self.assertTrue(
                alert_already_sent(
                    db,
                    alert_date=date.today(),
                    alert_type="RULE-HIGH",
                    category="dress",
                    phone="12345",
                )
            )
        finally:
            if db is not None:
                db.close()
            engine.dispose()

    def test_alert_dedup_ignores_failed_alerts(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine)
        db = None
        try:
            db = session_factory()
            db.add(
                Alert(
                    alert_date=date.today(),
                    alert_type="RULE-HIGH",
                    category="dress",
                    store_id=101,
                    recipient="Founder",
                    phone_number="12345",
                    message="Test",
                    capital_value=1000.0,
                    delivered=False,
                )
            )
            db.commit()

            self.assertFalse(
                alert_already_sent(
                    db,
                    alert_date=date.today(),
                    alert_type="RULE-HIGH",
                    category="dress",
                    phone="12345",
                )
            )
        finally:
            if db is not None:
                db.close()
            engine.dispose()

    def test_transfer_hint_prefers_healthy_peer_store(self):
        style_store_index = {
            "DRS-1001": [
                {
                    "store_id": 101,
                    "store_name": "Main",
                    "store_city": "Karachi",
                    "age_days": 310,
                    "status": "RR_TT",
                    "quantity": 22,
                },
                {
                    "store_id": 102,
                    "store_name": "North",
                    "store_city": "Lahore",
                    "age_days": 45,
                    "status": "HEALTHY",
                    "quantity": 6,
                },
            ]
        }
        hint = build_transfer_hint("DRS-1001", style_store_index, current_store_id=101)
        self.assertIn("doing well", hint)
        self.assertIn("Store 102", hint)
        self.assertIn("HEALTHY", hint)

    def test_transfer_hint_handles_missing_peer_data(self):
        style_store_index = {
            "DRS-1001": [
                {
                    "store_id": 101,
                    "store_name": "Main",
                    "store_city": "Karachi",
                    "age_days": 310,
                    "status": "RR_TT",
                    "quantity": 22,
                }
            ]
        }
        hint = build_transfer_hint("DRS-1001", style_store_index, current_store_id=101)
        self.assertIn("No peer-store data", hint)

    def test_resolve_alert_reason_prefers_rule_based_danger(self):
        self.assertEqual(_resolve_alert_reason("CRITICAL", 0.99), "RULE-CRITICAL")
        self.assertEqual(_resolve_alert_reason("HIGH", 0.99), "RULE-HIGH")

    def test_low_signal_ml_alert_filter(self):
        self.assertTrue(_is_low_signal_ml_alert("ML-RISK-ELEVATED", None, 10.0))
        self.assertFalse(_is_low_signal_ml_alert("ML-RISK-ELEVATED", "HIGH", 10.0))
        self.assertFalse(_is_low_signal_ml_alert("RULE-CRITICAL", "CRITICAL", 10.0))

    def test_recent_alert_sent_checks_cooldown_window(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine)
        db = None
        try:
            db = session_factory()
            today = date.today()
            db.add(
                Alert(
                    alert_date=today,
                    alert_type="RULE-HIGH",
                    category="dress",
                    store_id=101,
                    recipient="Founder",
                    phone_number="12345",
                    message="Test",
                    capital_value=1000.0,
                    delivered=True,
                )
            )
            db.commit()

            self.assertTrue(
                _recent_alert_sent(
                    db,
                    since_date=today,
                    alert_type="RULE-HIGH",
                    category="dress",
                    phone="12345",
                )
            )
            self.assertFalse(
                _recent_alert_sent(
                    db,
                    since_date=today,
                    alert_type="RULE-CRITICAL",
                    category="dress",
                    phone="12345",
                )
            )
        finally:
            if db is not None:
                db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
