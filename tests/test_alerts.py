import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.alert import Alert
from app.services.alert_service import alert_already_sent


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


if __name__ == "__main__":
    unittest.main()
