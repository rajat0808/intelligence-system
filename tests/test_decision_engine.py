import unittest

from app.core.decision_engine import evaluate_inventory


class DecisionEngineTest(unittest.TestCase):
    def test_critical_triggers_actions(self):
        result = evaluate_inventory("dress", 400, "M", "CRITICAL")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("RATE_REVISION", result["eligible_actions"])

    def test_non_critical_is_healthy(self):
        result = evaluate_inventory("dress", 10, "M", None)
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["eligible_actions"], [])

    def test_high_danger_triggers_transfer_action(self):
        result = evaluate_inventory("dress", 300, "M", "HIGH")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("PRIORITY_TRANSFER", result["eligible_actions"])

    def test_high_demand_keeps_transfer_review_off(self):
        result = evaluate_inventory("dress", 220, "H", None)
        self.assertEqual(result["status"], "HEALTHY")
        self.assertNotIn("TRANSFER_REVIEW", result["eligible_actions"])


if __name__ == "__main__":
    unittest.main()
