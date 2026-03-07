import os

import pytest

# Keep test runs independent from developer/local .env values.
os.environ.setdefault("IIP_DISABLE_DOTENV", "1")

from app.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
