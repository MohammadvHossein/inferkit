# InferKit Docs

## Installation

```bash
pip install inferkit              # lightweight core
pip install inferkit[vision]      # + Pillow
pip install inferkit[torch,transformers]
```

## Text (Simplest - 3 lines)

```python
from inferkit import infer
@infer
async def run(payload, files=None):
    return {"output": payload.get("text","")}
# sync is also supported:
# @infer
# def run(payload): return {"output": "sync"}
```

## Vision (Image Input)

```python
from inferkit import infer
from PIL import Image
import io
@infer
async def run(payload, files=None):
    if not files: return {"error": "no image"}
    img = Image.open(io.BytesIO(files[0]))
    return {"output": f"cat detected {img.size}"}
# client: curl -F payload='{"text":"hi"}' -F files=@cat.jpg http://localhost:8000/api/v1/infer
```

## Generation (Image Output - Recommended)

```python
from inferkit import infer, image_to_base64
from PIL import Image
@infer
async def run(payload, files=None):
    img = Image.new("RGB", (512,512), "red")
    return image_to_base64(img)  # {"image_base64": ..., "media_type": "image/png"}
# manual method also works:
# import base64, io; buf=io.BytesIO(); img.save(buf,format="PNG"); return {"image_base64": base64.b64encode(buf.getvalue()).decode()}
# or raw bytes: return buf.getvalue()
```

## Audio

```python
from inferkit import infer
@infer
async def run(payload, files=None):
    if not files: return {"error": "no audio"}
    audio_bytes = files[0]  # wav/mp3 bytes
    return {"transcript": "...", "bytes": len(audio_bytes)}
```

## LLM Streaming

```python
from inferkit import infer
@infer.stream
async def run_stream(payload):
    for tok in llm.stream(payload["text"]):
        yield tok
# sync generator also supported:
# @infer.stream
# def run_stream(payload):
#     for tok in payload["text"].split(): yield tok
```
Client:
- REST SSE: `POST /api/v1/infer/stream` with `{"text":"hello","stream":true}` -> `data: {"token": "..."}` + `data: [DONE]`
- WebSocket: `WS /ws/infer` with `{"text":"hi","stream":true}` or `{"text":"hi"}`

## Large Files

`.env`: `INFERKIT_MAX_UPLOAD_MB=50` (or `MAX_UPLOAD_MB`). Limit is checked on both `Content-Length` and `len(bytes)`, returns `413`.

## Authentication

`.env`: `INFERKIT_API_KEY=secret` -> client `X-API-Key: secret` or `?api_key=secret` (for WS)

## Environment Configuration (.env)

```
INFERKIT_HOST=0.0.0.0
INFERKIT_PORT=8000
INFERKIT_CORS_ORIGINS=["*"]   # or * or http://a.com,http://b.com
INFERKIT_MAX_UPLOAD_MB=50
INFERKIT_RATE_LIMIT=60/minute
INFERKIT_API_KEY=
INFERKIT_DEBUG=false
# plain names HOST/PORT/... also supported for backwards compatibility
```

## Optional Dependencies

```bash
pip install inferkit[vision]        # Pillow
pip install inferkit[torch]         # torch+torchvision
pip install inferkit[transformers]  # transformers+accelerate
pip install inferkit[all]           # all extras
pip install inferkit[dev]           # pytest, ruff, mypy
```

## Port and Firewall

If port 8000 is busy (`Not Found` or `Address already in use`):

```bash
inferkit dev inference.py --port 8001
# or
INFERKIT_PORT=8001 inferkit dev inference.py
```

Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "InferKit 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

Linux:

```bash
sudo ufw allow 8001/tcp
```

## Testing via Swagger

Open `http://localhost:8000/docs`:

- `GET /health` -> Try it out -> Execute -> `{"status":"ok"}`
- `POST /api/v1/infer/json` -> body `{"features":[5.1,3.5,1.4,0.2]}` -> Execute
- `POST /api/v1/infer/stream` -> `{"text":"hello world"}` for SSE
