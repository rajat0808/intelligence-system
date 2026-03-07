import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.routers.alerts import download_daily_alert_report_pdf


class AlertsRouterTest(unittest.TestCase):
    def test_download_daily_alert_report_pdf_returns_file_response(self):
        alerts = [
            {
                "title": "Example Product",
                "price": "Rs 100",
                "site": "Store 101",
                "image": "images/example.jpg",
            }
            for _ in range(50)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "daily_alert_report.pdf"
            report_path.write_bytes(b"%PDF-1.4\n%test\n")

            with patch(
                "app.routers.alerts.build_alerts_from_database",
                return_value=alerts,
            ), patch(
                "app.routers.alerts.generate_daily_alert_report",
                return_value=report_path,
            ):
                response = download_daily_alert_report_pdf(_auth=None)

        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.path, str(report_path))
        self.assertIn("attachment; filename=\"daily_alert_report.pdf\"", response.headers["content-disposition"])

    def test_download_daily_alert_report_pdf_returns_400_when_alerts_invalid(self):
        with patch(
            "app.routers.alerts.build_alerts_from_database",
            return_value=[],
        ), patch(
            "app.routers.alerts.generate_daily_alert_report",
            side_effect=ValueError("Expected at least 50 alerts, received 0."),
        ):
            with self.assertRaises(HTTPException) as error_context:
                download_daily_alert_report_pdf(_auth=None)

        self.assertEqual(error_context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
