import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path when running this script directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import setup_logging
from app.services.ingestion_service import import_workbook


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import daily updates from an Excel workbook."
    )
    parser.add_argument("--path", required=True, help="Path to .xlsx workbook.")
    parser.add_argument(
        "--sheets",
        nargs="*",
        default=None,
        help="Sheets to import (stores, products, inventory). Default: all found.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without saving.")
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()
    try:
        results = import_workbook(args.path, sheets=args.sheets, dry_run=args.dry_run)
    except (OSError, ValueError, SQLAlchemyError, InvalidFileException) as exc:
        raise SystemExit(f"Import failed: {exc}") from exc

    for sheet_name, counts in results.items():
        print(
            f"{sheet_name}: {counts['inserted']} inserted, "
            f"{counts['updated']} updated, {counts['skipped']} skipped"
        )
        price_changes = counts.get("price_changes") or []
        if price_changes:
            print("Price changes:")
            for change in price_changes:
                store_id = change.get("store_id", "--")
                style_code = change.get("style_code", "--")
                old_price = change.get("old_price", 0.0)
                new_price = change.get("new_price", 0.0)
                changed_at = change.get("changed_at", "--")
                print(
                    f"  store {store_id} | {style_code}: "
                    f"{old_price} -> {new_price} ({changed_at})"
                )

    if args.dry_run:
        print("Dry run complete, no changes committed.")
    else:
        print("Import complete.")


if __name__ == "__main__":
    main()
