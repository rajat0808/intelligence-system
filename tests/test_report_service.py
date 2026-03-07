import tempfile
import unittest
from pathlib import Path

from app.core.constants import STATIC_DIR
from app.services.report_service import ALERTS_PER_PDF, generate_daily_alert_report


class ReportServiceTest(unittest.TestCase):
    def test_generate_daily_alert_report_creates_pdf_with_exact_50_alerts(self):
        image_path = str(STATIC_DIR / "sindh-logo.png")
        alerts = [
            {
                "title": f"Example Product {index + 1}",
                "price": "Rs 999 | Qty 5",
                "site": "Store 101",
                "image": image_path,
            }
            for index in range(ALERTS_PER_PDF)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "daily_alert_report.pdf"
            report_path = generate_daily_alert_report(alerts, output_path=output_path)

            self.assertTrue(report_path.exists())
            self.assertEqual(report_path.name, "daily_alert_report.pdf")
            self.assertGreater(report_path.stat().st_size, 0)

    def test_generate_daily_alert_report_raises_when_alert_count_below_50(self):
        alerts = [
            {
                "title": "Only Alert",
                "price": "Rs 500",
                "site": "Store 101",
                "image": str(STATIC_DIR / "sindh-logo.png"),
            }
        ]
        with self.assertRaises(ValueError):
            generate_daily_alert_report(alerts, output_path="daily_alert_report.pdf")


if __name__ == "__main__":
    unittest.main()
