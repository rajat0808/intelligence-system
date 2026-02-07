import importlib
import sys
from pathlib import Path


def ensure_app_package():
    try:
        import app  # noqa: F401
        return
    except ModuleNotFoundError:
        # Allow running when the repo directory is not named "app".
        repo_root = Path(__file__).resolve().parent
        parent_dir = repo_root.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        sys.modules["app"] = importlib.import_module(repo_root.name)
