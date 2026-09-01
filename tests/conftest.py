import pytest
import inferkit.config as cfg
from inferkit.server import limiter


@pytest.fixture(autouse=True)
def _reset_state():
    try:
        limiter.reset()  # type: ignore
    except Exception:
        pass
    cfg.get_settings.cache_clear()
    yield
    try:
        limiter.reset()  # type: ignore
    except Exception:
        pass
    from inferkit.config import settings
    settings.api_key = None
    settings.rate_limit = "60/minute"
    settings.cors_origins = ["*"]
    settings.max_upload_mb = 50
    cfg.get_settings.cache_clear()
