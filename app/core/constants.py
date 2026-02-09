from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parent

TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

DANGER_LEVELS = ("EARLY", "HIGH", "CRITICAL")
AGING_STATUSES = ("HEALTHY", "TRANSFER", "RR_TT", "VERY_DANGER")

DEFAULT_DASHBOARD_PATH = "/dashboard"
