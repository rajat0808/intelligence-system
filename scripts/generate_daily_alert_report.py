import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path when running this script directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.report_service import (
    ALERTS_PER_PDF,
    create_and_send_daily_alert_report,
    generate_daily_alert_report,
)
from app.services.channels.telegram_service import send_telegram_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate daily_alert_report.pdf with exactly 50 alerts "
            "(text on left, image on right)."
        )
    )
    parser.add_argument(
        "--alerts-json",
        help=(
            "Optional JSON file containing alerts as a list of objects with keys: "
            "title, department, category, supplier, price (MRP), store (branch), "
            "stock_days, aging_status, purchase_report, cbs_qty, image."
        ),
    )
    parser.add_argument(
        "--output",
        default="daily_alert_report.pdf",
        help="Output PDF file path. Default: daily_alert_report.pdf",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send the generated PDF report to Telegram after creation.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=ALERTS_PER_PDF,
        help="Required number of alerts in the PDF. Default: 50",
    )
    return parser.parse_args()


def _load_alerts_from_json(path_value: str) -> list[dict]:
    file_path = Path(path_value)
    with file_path.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    if not isinstance(payload, list):
        raise ValueError("alerts-json must contain a JSON list of alert objects.")
    return payload


def main() -> int:
    args = parse_args()

    if args.alerts_json:
        alerts = _load_alerts_from_json(args.alerts_json)
        report_path = generate_daily_alert_report(
            alerts,
            output_path=args.output,
            expected_count=args.expected_count,
        )
        sent = False
        if args.send_telegram:
            sent = send_telegram_document(
                report_path,
                caption="Daily alert report ({} alerts)".format(args.expected_count),
            )
        result = {
            "path": str(report_path),
            "alerts": args.expected_count,
            "sent_to_telegram": sent,
        }
    else:
        result = create_and_send_daily_alert_report(
            output_path=args.output,
            send_to_telegram=args.send_telegram,
            expected_count=args.expected_count,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
