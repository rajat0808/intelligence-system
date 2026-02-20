import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.alert import Alert
from app.services.alert_service import _build_transfer_hint, alert_already_sent


class AlertServiceTest(unittest.TestCase):
    def test_alert_dedup(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)

        db = Session()
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
        db.close()

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
        hint = _build_transfer_hint("DRS-1001", style_store_index, current_store_id=101)
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
        hint = _build_transfer_hint("DRS-1001", style_store_index, current_store_id=101)
        self.assertIn("No peer-store data", hint)


if __name__ == "__main__":
    unittest.main()
