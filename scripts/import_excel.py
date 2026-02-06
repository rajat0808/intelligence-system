import argparse
import importlib
import sys
from pathlib import Path

from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import SQLAlchemyError

def _ensure_app_package():
    try:
        import app  # noqa: F401
        return
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[1]
        parent_dir = repo_root.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        sys.modules["app"] = importlib.import_module(repo_root.name)


_ensure_app_package()

from app.services.excel_importer import import_workbook


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
