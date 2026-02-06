import unittest
from datetime import date, timedelta

from intelligence.danger_rules import danger_level


class DangerRulesTest(unittest.TestCase):
    def test_boundaries(self):
        today = date.today()
        cases = [
            (179, None),
            (180, "EARLY"),
            (249, "EARLY"),
            (250, "HIGH"),
            (364, "HIGH"),
            (365, "CRITICAL"),
        ]
        for days, expected in cases:
            with self.subTest(days=days):
                start_date = today - timedelta(days=days)
                self.assertEqual(danger_level(start_date), expected)


if __name__ == "__main__":
    unittest.main()
