import logging
import threading
from pathlib import Path

from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import SQLAlchemyError

from services.excel_importer import import_workbook, normalize_sheet_list

logger = logging.getLogger(__name__)


def ensure_datasource_dir(path):
    datasource_dir = Path(path)
    datasource_dir.mkdir(parents=True, exist_ok=True)
    return datasource_dir


def summarize_results(results):
    parts = []
    for sheet_name, counts in results.items():
        parts.append(
            "{}: {} inserted, {} updated".format(
                sheet_name,
                counts.get("inserted", 0),
                counts.get("updated", 0),
            )
        )
    return "; ".join(parts) if parts else "no rows"


class ExcelWatchService:
    def __init__(self, watch_dir, poll_seconds=10, sheets=None):
        self.watch_dir = Path(watch_dir)
        self.poll_seconds = max(2, int(poll_seconds))
        self.sheets = normalize_sheet_list(sheets)
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._seen = {}
        self._processed = {}

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        ensure_datasource_dir(self.watch_dir)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="excel-auto-import",
            daemon=True,
        )
        self._thread.start()
        logger.info("Excel auto-import watching: %s", self.watch_dir)

    def stop(self):
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=self.poll_seconds + 1)
        self._thread = None
        logger.info("Excel auto-import stopped")

    def _run(self):
        while not self._stop_event.is_set():
            self._scan_once()
            self._stop_event.wait(self.poll_seconds)

    def _scan_once(self):
        if not self.watch_dir.exists():
            return
        for file_path in sorted(self.watch_dir.glob("*.xlsx")):
            if not self._is_candidate(file_path):
                continue
            if not self._is_ready(file_path):
                continue
            self._import_file(file_path)

    def _is_candidate(self, file_path):
        if not file_path.is_file():
            return False
        if file_path.name.startswith("~$"):
            return False
        return True

    def _is_ready(self, file_path):
        try:
            stat = file_path.stat()
        except OSError:
            return False
        key = (stat.st_mtime, stat.st_size)
        last_seen = self._seen.get(file_path)
        self._seen[file_path] = key
        if last_seen != key:
            return False
        last_processed = self._processed.get(file_path)
        if last_processed is None or stat.st_mtime > last_processed:
            return True
        return False

    def _import_file(self, file_path):
        with self._lock:
            try:
                stat = file_path.stat()
            except OSError:
                return
            try:
                results = import_workbook(file_path, sheets=self.sheets, dry_run=False)
            except (OSError, ValueError, SQLAlchemyError, InvalidFileException) as exc:
                logger.exception("Excel import failed for %s: %s", file_path, exc)
                return
            self._processed[file_path] = stat.st_mtime
            logger.info(
                "Excel import completed for %s: %s",
                file_path,
                summarize_results(results),
            )
