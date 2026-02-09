import argparse

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

    if args.dry_run:
        print("Dry run complete, no changes committed.")
    else:
        print("Import complete.")


if __name__ == "__main__":
    main()