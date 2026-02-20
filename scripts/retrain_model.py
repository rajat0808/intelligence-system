import sys
from pathlib import Path

# Ensure repo root is on sys.path when running this script directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.ml.train import main


if __name__ == "__main__":
    main()
