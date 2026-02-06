import unittest

from intelligence.decision_engine import evaluate_inventory


class DecisionEngineTest(unittest.TestCase):
    def test_critical_triggers_actions(self):
        result = evaluate_inventory("dress", 400, "M", "CRITICAL")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("RATE_REVISION", result["eligible_actions"])

    def test_non_critical_is_healthy(self):
        result = evaluate_inventory("dress", 10, "M", None)
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["eligible_actions"], [])


if __name__ == "__main__":
    unittest.main()
