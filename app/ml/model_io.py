from __future__ import annotations

from pathlib import Path
import json

import joblib

from app.config import get_settings


_DEFAULT_MODEL_NAME = "inventory_risk_model.joblib"
_DEFAULT_METADATA_NAME = "inventory_risk_metadata.json"


def get_model_paths(model_path=None, metadata_path=None):
    settings = get_settings()
    base_dir = Path(__file__).resolve().parent / "artifacts"

    model_value = model_path or settings.ML_MODEL_PATH or str(base_dir / _DEFAULT_MODEL_NAME)
    metadata_value = (
        metadata_path
        or settings.ML_MODEL_METADATA_PATH
        or str(base_dir / _DEFAULT_METADATA_NAME)
    )

    return Path(model_value), Path(metadata_value)


def model_available(model_path=None) -> bool:
    path, _ = get_model_paths(model_path=model_path)
    return path.exists()


def save_model(model, metadata, model_path=None, metadata_path=None):
    model_file, metadata_file = get_model_paths(model_path, metadata_path)
    model_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_file)
    with metadata_file.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
    return model_file, metadata_file


def load_model(model_path=None, metadata_path=None):
    model_file, metadata_file = get_model_paths(model_path, metadata_path)
    if not model_file.exists():
        return None, None
    model = joblib.load(model_file)
    metadata = None
    if metadata_file.exists():
        with metadata_file.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
    return model, metadata
