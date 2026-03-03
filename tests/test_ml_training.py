import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app.ml.train import _build_weak_label_training_set, build_training_data


class MLTrainingFallbackTest(unittest.TestCase):
    @staticmethod
    def _sample_inventory_rows():
        today = date.today()
        return [
            {
                "store_id": 1,
                "product_id": 101,
                "category": "LEHENGA BRIDAL",
                "quantity": 80,
                "cost_price": 3500,
                "current_price": 3300,
                "mrp": 5000,
                "department_name": "ETHNIC",
                "supplier_name": "Vendor A",
                "lifecycle_start_date": today - timedelta(days=500),
            },
            {
                "store_id": 1,
                "product_id": 102,
                "category": "DRESS",
                "quantity": 4,
                "cost_price": 900,
                "current_price": 850,
                "mrp": 1200,
                "department_name": "APPAREL",
                "supplier_name": "Vendor B",
                "lifecycle_start_date": today - timedelta(days=21),
            },
            {
                "store_id": 2,
                "product_id": 201,
                "category": "SAREE",
                "quantity": 30,
                "cost_price": 1500,
                "current_price": 1400,
                "mrp": 2200,
                "department_name": "SAREE",
                "supplier_name": "Vendor C",
                "lifecycle_start_date": today - timedelta(days=240),
            },
            {
                "store_id": 2,
                "product_id": 202,
                "category": "DRESS MATERIAL",
                "quantity": 7,
                "cost_price": 700,
                "current_price": 650,
                "mrp": 1000,
                "department_name": "FABRIC",
                "supplier_name": "Vendor D",
                "lifecycle_start_date": today - timedelta(days=45),
            },
        ]

    def test_weak_label_training_set_builds_features_and_two_classes(self):
        rows = self._sample_inventory_rows()
        features, labels, dates = _build_weak_label_training_set(rows, as_of_date=date.today())

        self.assertEqual(len(features), len(rows))
        self.assertEqual(len(labels), len(rows))
        self.assertEqual(len(dates), len(rows))
        self.assertEqual(set(labels), {0, 1})

    def test_build_training_data_uses_weak_labels_without_sales(self):
        rows = self._sample_inventory_rows()
        with patch("app.ml.train._load_sales", return_value=[]), patch(
            "app.ml.train._load_inventory",
            return_value=rows,
        ):
            features, labels, dates, source = build_training_data(
                engine=object(),
                horizon_days=30,
                as_of_date=date.today(),
            )

        self.assertEqual(source, "inventory+weak_labels_no_sales")
        self.assertEqual(len(features), len(rows))
        self.assertEqual(set(labels), {0, 1})
        self.assertEqual(len(dates), len(rows))

    def test_build_training_data_without_inventory_raises(self):
        with patch("app.ml.train._load_sales", return_value=[]), patch(
            "app.ml.train._load_inventory",
            return_value=[],
        ):
            with self.assertRaises(ValueError):
                build_training_data(engine=object(), horizon_days=30)


if __name__ == "__main__":
    unittest.main()
