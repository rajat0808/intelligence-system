import unittest

from app.services.ingestion_service import normalize_header, normalize_sheet_list


class IngestionServiceTest(unittest.TestCase):
    def test_header_aliases(self):
        self.assertEqual(normalize_header("Style Code"), "style_code")
        self.assertEqual(normalize_header("Item MRP"), "mrp")
        self.assertEqual(normalize_header("Lifecycle Start Date"), "lifecycle_start_date")

    def test_normalize_sheet_list(self):
        self.assertEqual(
            normalize_sheet_list("stores, products, inventory"),
            ["stores", "products", "inventory"],
        )


if __name__ == "__main__":
    unittest.main()
