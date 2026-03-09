import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.core.constants import STATIC_DIR
from app.services.report_service import (
    ALERTS_PER_PDF,
    _build_grouped_alerts_from_rows,
    _coerce_alert,
    _normalize_alerts,
    _resolve_aging_badge_style,
    create_and_send_daily_alert_reports,
    generate_daily_alert_report,
    resolve_image_path,
)


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

    def test_resolve_image_path_supports_static_url(self):
        image_path = resolve_image_path("http://127.0.0.1:8000/static/sindh-logo.png")
        self.assertEqual(image_path, STATIC_DIR / "sindh-logo.png")

    def test_resolve_image_path_supports_static_query_string(self):
        image_path = resolve_image_path("/static/sindh-logo.png?v=20260309")
        self.assertEqual(image_path, STATIC_DIR / "sindh-logo.png")

    def test_coerce_alert_includes_cumulative_quantity(self):
        alert = _coerce_alert({"title": "Demo Product"})
        self.assertIn("cumulative_quantity", alert)
        self.assertEqual(alert["cumulative_quantity"], "")

    def test_resolve_aging_badge_style_maps_colors(self):
        status, bg_color, text_color = _resolve_aging_badge_style("very_danger")
        self.assertEqual(status, "VERY_DANGER")
        self.assertEqual(bg_color, "#FECACA")
        self.assertEqual(text_color, "#991B1B")

    def test_normalize_alerts_computes_cumulative_qty_per_style(self):
        alerts = [
            {"title": "A", "style_code": "PSD3-80413", "quantity": "1"},
            {"title": "B", "style_code": "PSD3-80413", "quantity": "1"},
            {"title": "C", "style_code": "PSD3-80413", "quantity": "1"},
            {"title": "D", "style_code": "X-1", "quantity": "2"},
        ]
        normalized = _normalize_alerts(alerts, expected_count=4)
        cumulative_values = [item["cumulative_quantity"] for item in normalized]
        self.assertEqual(cumulative_values, ["3", "3", "3", "2"])

    def test_build_grouped_alerts_from_rows_matches_style_case_across_stores(self):
        rows = [
            SimpleNamespace(
                article_name="Sample Product",
                style_code="PSD3-80413",
                category="dress",
                mrp=4595,
                image_url="/static/images/3013.jpg",
                store_id=1,
                store_name="Store 1",
                store_city="Unknown",
                quantity=1,
                lifecycle_start_date=date(2026, 2, 20),
            ),
            SimpleNamespace(
                article_name="Sample Product",
                style_code="psd3-80413",
                category="dress",
                mrp=4595,
                image_url="/static/images/3013.jpg",
                store_id=2,
                store_name="Store 2",
                store_city="Unknown",
                quantity=2,
                lifecycle_start_date=date(2026, 2, 21),
            ),
        ]
        grouped = _build_grouped_alerts_from_rows(rows, today=date(2026, 3, 9))
        self.assertEqual(len(grouped), 1)
        alert = grouped[0]
        self.assertEqual(alert["style_code"], "PSD3-80413")
        self.assertEqual(alert["quantity"], "3")
        self.assertEqual(alert["cumulative_quantity"], "3")
        self.assertIn("2 stores", alert["site"])
        self.assertIn("HEAD OFFICE", alert["store"])
        self.assertIn("Store 2", alert["store"])

    def test_create_and_send_daily_alert_reports_generates_max_three_pdfs(self):
        image_path = str(STATIC_DIR / "sindh-logo.png")
        alerts = [
            {
                "title": f"Example Product {index + 1}",
                "price": "Rs 999 | Qty 5",
                "site": "Store 101",
                "image": image_path,
            }
            for index in range(ALERTS_PER_PDF * 4)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "daily_alert_report.pdf"
            summary = create_and_send_daily_alert_reports(
                alerts=alerts,
                output_path=output_path,
                send_to_telegram=False,
                expected_count=ALERTS_PER_PDF,
                max_reports_per_day=3,
                report_date=date(2026, 3, 9),
            )

            self.assertEqual(summary["generated_reports"], 3)
            self.assertEqual(len(summary["reports"]), 3)
            for report in summary["reports"]:
                self.assertEqual(report["alerts"], ALERTS_PER_PDF)
                self.assertTrue(Path(report["path"]).exists())

    def test_create_and_send_daily_alert_reports_skips_when_daily_limit_reached(self):
        image_path = str(STATIC_DIR / "sindh-logo.png")
        alerts = [
            {
                "title": f"Example Product {index + 1}",
                "price": "Rs 999 | Qty 5",
                "site": "Store 101",
                "image": image_path,
            }
            for index in range(ALERTS_PER_PDF * 3)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            for report_index in (1, 2, 3):
                existing_path = output_dir / f"daily_alert_report_20260309_{report_index}.pdf"
                existing_path.write_bytes(b"%PDF-1.4\n%existing\n")

            summary = create_and_send_daily_alert_reports(
                alerts=alerts,
                output_path=output_dir / "daily_alert_report.pdf",
                send_to_telegram=False,
                expected_count=ALERTS_PER_PDF,
                max_reports_per_day=3,
                report_date=date(2026, 3, 9),
            )

            self.assertEqual(summary["generated_reports"], 0)
            self.assertEqual(len(summary["reports"]), 0)
            self.assertIn("Daily PDF limit already reached", str(summary["skipped_reason"]))

    def test_create_and_send_daily_alert_reports_unlimited_generates_new_indices(self):
        image_path = str(STATIC_DIR / "sindh-logo.png")
        alerts = [
            {
                "title": f"Example Product {index + 1}",
                "price": "Rs 999 | Qty 5",
                "site": "Store 101",
                "image": image_path,
            }
            for index in range(ALERTS_PER_PDF * 4)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            for report_index in (1, 2, 3):
                existing_path = output_dir / f"daily_alert_report_20260309_{report_index}.pdf"
                existing_path.write_bytes(b"%PDF-1.4\n%existing\n")

            summary = create_and_send_daily_alert_reports(
                alerts=alerts,
                output_path=output_dir / "daily_alert_report.pdf",
                send_to_telegram=False,
                expected_count=ALERTS_PER_PDF,
                max_reports_per_day=0,
                report_date=date(2026, 3, 9),
            )

            self.assertEqual(summary["reports_limit"], 0)
            self.assertEqual(summary["generated_reports"], 4)
            self.assertEqual(len(summary["reports"]), 4)
            self.assertEqual(
                [item["report_index"] for item in summary["reports"]],
                [4, 5, 6, 7],
            )


if __name__ == "__main__":
    unittest.main()
