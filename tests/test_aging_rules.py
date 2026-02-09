import unittest

from app.core.aging_rules import classify_status


class AgingRulesTest(unittest.TestCase):
    def test_dress(self):
        self.assertEqual(classify_status("dress", 90), "HEALTHY")
        self.assertEqual(classify_status("dress", 180), "TRANSFER")
        self.assertEqual(classify_status("dress", 365), "RR_TT")
        self.assertEqual(classify_status("dress", 366), "VERY_DANGER")

    def test_dress_material(self):
        self.assertEqual(classify_status("dress material", 90), "HEALTHY")
        self.assertEqual(classify_status("dress material", 180), "TRANSFER")
        self.assertEqual(classify_status("dress material", 181), "RR_TT")
        self.assertEqual(classify_status("dress material", 366), "VERY_DANGER")

    def test_lehenga(self):
        self.assertEqual(classify_status("lehenga", 250), "HEALTHY")
        self.assertEqual(classify_status("lehenga", 365), "TRANSFER")
        self.assertEqual(classify_status("lehenga", 366), "VERY_DANGER")

    def test_saree(self):
        self.assertEqual(classify_status("saree", 365), "HEALTHY")
        self.assertEqual(classify_status("saree", 366), "VERY_DANGER")

    def test_unknown_category(self):
        with self.assertRaises(ValueError):
            classify_status("unknown", 10)


if __name__ == "__main__":
    unittest.main()
