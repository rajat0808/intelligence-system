import unittest

from pydantic import ValidationError

from app.schemas.inventory import ExcelIngestRequest, InventoryCreate
from app.schemas.ml import MLPredictRequest


class SchemaValidationTest(unittest.TestCase):
    def test_ml_predict_request_rejects_non_positive_quantity(self):
        with self.assertRaises(ValidationError):
            MLPredictRequest(
                category="GOWN",
                quantity=0,
                item_mrp=1000,
                lifecycle_start_date="2026-01-01",
            )

    def test_ml_predict_request_rejects_invalid_store_id(self):
        with self.assertRaises(ValidationError):
            MLPredictRequest(
                category="GOWN",
                quantity=10,
                item_mrp=1000,
                lifecycle_start_date="2026-01-01",
                store_id=0,
            )

    def test_inventory_create_rejects_negative_quantity(self):
        with self.assertRaises(ValidationError):
            InventoryCreate(
                store_id=1,
                product_id=1,
                quantity=-1,
                item_mrp=1000,
                current_price=900,
                lifecycle_start_date="2026-01-01",
            )

    def test_excel_ingest_request_normalizes_path(self):
        payload = ExcelIngestRequest(path="  datasource/daily_update.xlsx  ")
        self.assertEqual(payload.path, "datasource/daily_update.xlsx")


if __name__ == "__main__":
    unittest.main()
