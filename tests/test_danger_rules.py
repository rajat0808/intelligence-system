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

    def test_accepts_iso_date_string(self):
        today = date.today()
        start_date = (today - timedelta(days=180)).isoformat()
        self.assertEqual(danger_level(start_date), "EARLY")


if __name__ == "__main__":
    unittest.main()
