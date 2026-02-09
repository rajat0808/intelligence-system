import unittest
from datetime import date, timedelta

from app.ml.predict import predict_risk


class MLServiceTest(unittest.TestCase):
    def test_predict_risk_range(self):
        score = predict_risk(
            category="dress",
            quantity=10,
            cost_price=2500.0,
            lifecycle_start_date=date.today() - timedelta(days=120),
        )
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
