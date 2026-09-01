import base64
import io
import pathlib
import importlib.util

import pytest
from fastapi.testclient import TestClient

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

from inferkit.registry import set_run, set_stream
from inferkit.server import create_app

def load_example():
    p = pathlib.Path("examples/my_model.py")
    spec = importlib.util.spec_from_file_location("user_model", str(p))
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod

@pytest.fixture
def client():
    load_example()
    app = create_app()
    return TestClient(app)

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_infer_json_text(client):
    r = client.post("/api/v1/infer/json", json={"text": "hello"})
    assert r.status_code == 200
    assert "output" in r.json()

def test_infer_json_image_out(client):
    if Image is None:
        pytest.skip("Pillow not installed")
    r = client.post("/api/v1/infer/json", json={"mode": "image_out"})
    assert r.status_code == 200
    data = r.json()
    assert "image_base64" in data
    img_bytes = base64.b64decode(data["image_base64"])
    img = Image.open(io.BytesIO(img_bytes))
    assert img.size == (256, 256)

def test_infer_sync_function():
    from inferkit import infer
    from inferkit.registry import set_run

    @infer
    def sync_run(payload):
        return {"output": "sync:" + payload.get("text", "")}

    app = create_app()
    c = TestClient(app)
    r = c.post("/api/v1/infer/json", json={"text": "hi"})
    assert r.status_code == 200
    assert r.json()["output"] == "sync:hi"
    load_example()

def test_infer_stream(client):
    r = client.post("/api/v1/infer/stream", json={"text": "hello world"})
    assert r.status_code == 200
    assert "data:" in r.text

def test_file_upload(client):
    buf = io.BytesIO(b"fake image")
    r = client.post("/api/v1/infer", data={"payload": '{"text":"hi"}'}, files={"files": ("test.jpg", buf, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["output"].startswith("received")

def test_root_and_info(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/info").status_code == 200
    assert client.get("/metrics").status_code == 200

def test_invalid_json(client):
    r = client.post("/api/v1/infer", data={"payload": "not-json"}, files={})
    assert r.status_code == 400

def test_bytes_return():
    from inferkit import infer

    @infer
    async def bytes_run(payload, files=None):
        return b"\x89PNG"

    app = create_app()
    c = TestClient(app)
    r = c.post("/api/v1/infer/json", json={"text": "hi"})
    assert r.content.startswith(b"\x89PNG")
    load_example()

def test_websocket(client):
    with client.websocket_connect("/ws/infer") as ws:
        ws.send_text('{"text":"hello"}')
        data = ws.receive_text()
        assert "output" in data
