# InferKit - Deploy any AI function in 3 lines

Library for ML / Vision / LLM / Agent. No FastAPI boilerplate needed.

## Install
```bash
pip install inferkit
# local dev
pip install -e .
```

## Usage - 3 lines
```python
# my_model.py
from inferkit import infer

@infer
async def run(payload, files=None):
    # payload: {"text": "..."}  files: list[bytes] for images/audio
    return {"output": f"echo: {payload.get('text')}"}

@infer.stream  # optional for LLM streaming
async def run_stream(payload):
    for tok in payload.get("text","").split():
        yield tok + " "
```

Run:
```bash
inferkit dev my_model.py --port 8000
# docs at http://localhost:8000/docs
```

Endpoints auto created:
- `POST /api/v1/infer` (multipart file + json)
- `POST /api/v1/infer/json` (json only)
- `POST /api/v1/infer/stream` (SSE)
- `WS /ws/infer` (WebSocket + streaming + image base64)

Image output: `return {"image_base64": b64, "media_type": "image/png"}` or `return png_bytes`

## Init new project
```bash
inferkit init
# creates .env.example, Dockerfile
```

## Deploy (one command, any OS, auto detects Docker)
```bash
inferkit deploy
# if docker available -> docker compose/build
# else -> venv + uvicorn --workers 4 on 0.0.0.0:8000
```

## Config via .env
```
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["*"]
MAX_UPLOAD_MB=50
RATE_LIMIT=60/minute
API_KEY=  # if set, require X-API-Key header
DEBUG=false
```

## Programmatic
```python
from inferkit import serve
serve("my_model.py", port=8000)
```
