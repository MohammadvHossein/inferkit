import io
import pathlib
import importlib.util

import pytest
from fastapi.testclient import TestClient

from inferkit.server import create_app, limiter


def load_example():
    p = pathlib.Path("examples/my_model.py")
    spec = importlib.util.spec_from_file_location("user_model", str(p))
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def reset_limiter():
    try:
        limiter.reset()  # type: ignore
    except Exception:
        try:
            limiter._storage.reset()  # type: ignore
        except Exception:
            pass


@pytest.fixture(autouse=False)
def client():
    load_example()
    app = create_app()
    return TestClient(app)


def test_rate_limit_429():
    load_example()
    from inferkit.config import settings
    import inferkit.config as cfg

    orig = settings.rate_limit
    settings.rate_limit = "2/minute"
    reset_limiter()
    app = create_app()
    c = TestClient(app)
    for _ in range(2):
        r = c.post("/api/v1/infer/json", json={"text": "hi"})
        assert r.status_code == 200
    r = c.post("/api/v1/infer/json", json={"text": "hi"})
    assert r.status_code == 429
    assert "rate limit" in r.json()["error"].lower()
    settings.rate_limit = orig
    reset_limiter()
    cfg.get_settings.cache_clear()


def test_api_key_rest_and_ws():
    load_example()
    from inferkit.config import settings
    import inferkit.config as cfg

    reset_limiter()
    cfg.get_settings.cache_clear()
    settings.api_key = "secret123"
    try:
        app = create_app()
        c = TestClient(app, raise_server_exceptions=False)
        r = c.post("/api/v1/infer/json", json={"text": "hi"})
        assert r.status_code == 401
        r = c.post("/api/v1/infer/json", json={"text": "hi"}, headers={"X-API-Key": "secret123"})
        assert r.status_code == 200
        try:
            with c.websocket_connect("/ws/infer") as ws:
                ws.send_text('{"text":"hi"}')
                ws.receive_text()
            assert False, "should block without key"
        except Exception:
            pass
        with c.websocket_connect("/ws/infer?api_key=secret123") as ws:
            ws.send_text('{"text":"hi"}')
            data = ws.receive_text()
            assert "output" in data
    finally:
        settings.api_key = None
        cfg.get_settings.cache_clear()
        reset_limiter()


def test_upload_size_limit():
    load_example()
    from inferkit.config import settings
    import inferkit.config as cfg

    reset_limiter()
    cfg.get_settings.cache_clear()
    old_key = settings.api_key
    settings.api_key = None
    settings.max_upload_mb = 1
    try:
        app = create_app()
        c = TestClient(app, raise_server_exceptions=False)
        big = b"x" * (2 * 1024 * 1024)
        buf = io.BytesIO(big)
        r = c.post("/api/v1/infer", data={"payload": '{"text":"hi"}'}, files={"files": ("big.jpg", buf, "image/jpeg")})
        assert r.status_code == 413
    finally:
        settings.max_upload_mb = 50
        settings.api_key = old_key
        cfg.get_settings.cache_clear()
        reset_limiter()


def test_payload_too_large():
    load_example()
    from inferkit.config import settings

    reset_limiter()
    old_key = settings.api_key
    settings.api_key = None
    try:
        app = create_app()
        c = TestClient(app, raise_server_exceptions=False)
        huge = "x" * (2 * 1024 * 1024)
        r = c.post("/api/v1/infer/json", json={"text": huge})
        assert r.status_code == 413
    finally:
        settings.api_key = old_key
        reset_limiter()


def test_cors_credentials_false_when_wildcard():
    load_example()
    from inferkit.config import settings
    import inferkit.config as cfg

    reset_limiter()
    cfg.get_settings.cache_clear()
    settings.cors_origins = ["*"]
    app = create_app()
    cors = [m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"][0]
    assert cors.kwargs["allow_credentials"] is False
    settings.cors_origins = ["http://a.com"]
    app2 = create_app()
    cors2 = [m for m in app2.user_middleware if m.cls.__name__ == "CORSMiddleware"][0]
    assert cors2.kwargs["allow_credentials"] is True
    cfg.get_settings.cache_clear()
    settings.cors_origins = ["*"]
    reset_limiter()


def test_metrics_and_helpers():
    load_example()
    reset_limiter()
    pytest.importorskip("PIL")
    from inferkit import image_to_base64
    from PIL import Image

    app = create_app()
    c = TestClient(app)
    r = c.get("/metrics")
    assert r.status_code == 200
    assert "requests" in r.json()
    img = Image.new("RGB", (10, 10), "red")
    res = image_to_base64(img)
    assert "image_base64" in res
    assert res["media_type"] == "image/png"
    reset_limiter()


def test_config_prefix_both():
    import os
    import inferkit.config as cfg

    reset_limiter()
    cfg.get_settings.cache_clear()
    os.environ["HOST"] = "127.0.0.2"
    s = cfg.Settings()
    assert s.host == "127.0.0.2"
    os.environ.pop("HOST", None)
    os.environ["INFERKIT_HOST"] = "127.0.0.3"
    cfg.get_settings.cache_clear()
    s2 = cfg.Settings()
    assert s2.host == "127.0.0.3"
    os.environ.pop("INFERKIT_HOST", None)
    cfg.get_settings.cache_clear()
    os.environ["INFERKIT_CORS_ORIGINS"] = "http://a.com,http://b.com"
    s3 = cfg.Settings()
    assert s3.cors_origins == ["http://a.com", "http://b.com"]
    os.environ.pop("INFERKIT_CORS_ORIGINS", None)
    cfg.get_settings.cache_clear()
    reset_limiter()
