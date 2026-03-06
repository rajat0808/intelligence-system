import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app.ml import predict as predict_module
from app.ml.predict import get_model_runtime_info, model_is_available, predict_risk


class PredictRiskTest(unittest.TestCase):
    def setUp(self):
        self._model_state = (
            predict_module._MODEL,
            predict_module._MODEL_METADATA,
            predict_module._MODEL_LOAD_ERROR,
        )

    def tearDown(self):
        (
            predict_module._MODEL,
            predict_module._MODEL_METADATA,
            predict_module._MODEL_LOAD_ERROR,
        ) = self._model_state

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

    def test_runtime_info_uses_fallback_when_model_missing(self):
        predict_module._MODEL = None
        predict_module._MODEL_METADATA = None
        predict_module._MODEL_LOAD_ERROR = None

        with patch.object(predict_module, "model_available", return_value=False), patch.object(
            predict_module,
            "load_model",
            return_value=(None, None),
        ):
            status = get_model_runtime_info()

        self.assertEqual(status["mode"], "heuristic_fallback")
        self.assertFalse(status["model_available"])
        self.assertFalse(status["model_loaded"])
        self.assertEqual(status["load_error"], "model artifact not found")

    def test_model_loader_retries_after_missing_artifact_appears(self):
        model_obj = object()
        predict_module._MODEL = None
        predict_module._MODEL_METADATA = None
        predict_module._MODEL_LOAD_ERROR = "missing"

        with patch.object(
            predict_module,
            "model_available",
            side_effect=[False, True],
        ), patch.object(
            predict_module,
            "load_model",
            return_value=(model_obj, {"training_source": "inventory+weak_labels_no_sales"}),
        ):
            first = predict_module._load_model_once()
            second = predict_module._load_model_once()

        self.assertIsNone(first)
        self.assertIs(second, model_obj)
        self.assertIs(predict_module._MODEL, model_obj)
        self.assertEqual(
            predict_module._MODEL_METADATA["training_source"],
            "inventory+weak_labels_no_sales",
        )

    def test_weak_label_model_prediction_is_blended_with_heuristic(self):
        class AlwaysOneModel:
            @staticmethod
            def predict_proba(_rows):
                return [[0.0, 1.0]]

        predict_module._MODEL = AlwaysOneModel()
        predict_module._MODEL_METADATA = {"training_source": "inventory+weak_labels_no_sales"}
        predict_module._MODEL_LOAD_ERROR = None

        score = predict_risk(
            category="dress",
            quantity=1,
            cost_price=100.0,
            lifecycle_start_date=date.today(),
        )
        self.assertGreaterEqual(score, 0.02)
        self.assertLess(score, 1.0)


if __name__ == "__main__":
    unittest.main()
