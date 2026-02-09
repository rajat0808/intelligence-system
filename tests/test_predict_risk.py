import unittest
from datetime import date, timedelta

from app.ml.predict import predict_risk, model_is_available


class PredictRiskTest(unittest.TestCase):
    def test_risk_bounds(self):
        today = date.today()
        risk = predict_risk("dress", 1, 100, today)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)

    def test_risk_increases_with_age(self):
        if model_is_available():
            self.skipTest("Trained model available; monotonic check not applicable.")
        today = date.today()
        fresh = predict_risk("dress", 1, 100, today)
        older = predict_risk("dress", 1, 100, today - timedelta(days=200))
        self.assertGreaterEqual(older, fresh)

    def test_risk_increases_with_value(self):
        if model_is_available():
            self.skipTest("Trained model available; monotonic check not applicable.")
        today = date.today()
        low_value = predict_risk("saree", 1, 10, today)
        high_value = predict_risk("saree", 1000, 1000, today)
        self.assertGreaterEqual(high_value, low_value)
        self.assertLessEqual(high_value, 1.0)


if __name__ == "__main__":
    unittest.main()
