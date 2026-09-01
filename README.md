# InferKit - Deploy any AI function in 3 lines

Library for ML / Vision / LLM / Agent. No FastAPI boilerplate needed.

## Install
```bash
pip install inferkit              # core (no Pillow)
pip install inferkit[vision]      # + Pillow for image in/out
pip install inferkit[torch,transformers]  # heavy ML stacks
pip install -e .[dev]             # local dev
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
inferkit serve my_model.py --port 8001
# docs at http://localhost:8001/docs
```

Endpoints auto created:
- `POST /api/v1/infer` (multipart file + json)
- `POST /api/v1/infer/json` (json only)
- `POST /api/v1/infer/stream` (SSE)
- `WS /ws/infer` and `WS /api/v1/ws/infer` (WebSocket + streaming)

Image output helpers:
```python
from inferkit import image_to_base64, bytes_to_response
from PIL import Image
return image_to_base64(Image.new("RGB",(512,512),"red"))
return bytes_to_response(png_bytes, "image/png")
# also still supported: return {"image_base64": b64} or return png_bytes
```

## Init new project
```bash
inferkit init
# creates .env.example, .env, Dockerfile, my_model.py
```

## Deploy (one command, any OS, auto detects Docker)
```bash
inferkit deploy
# if docker available -> docker compose/build
# else -> venv + uvicorn on INFERKIT_HOST:INFERKIT_PORT
```

## Config via .env
```
INFERKIT_HOST=0.0.0.0
INFERKIT_PORT=8000
INFERKIT_CORS_ORIGINS=["*"]   # or * or http://a.com,http://b.com
INFERKIT_MAX_UPLOAD_MB=50
INFERKIT_RATE_LIMIT=60/minute
INFERKIT_API_KEY=            # if set, require X-API-Key header (also ?api_key=)
INFERKIT_DEBUG=false
# plain HOST/PORT/CORS_ORIGINS also work for backwards compat
```

## Tutorial (0 to 100)

Complete guide with training and checkpoint: [`tutorial/00-100-complete-guide.md`](tutorial/00-100-complete-guide.md)

```bash
python tutorial/train_example.py      # train and save checkpoints/model.pkl
inferkit serve tutorial/inference_example.py --port 8001  # serve
```

## Programmatic
```python
from inferkit import serve
serve("my_model.py", port=8000)
```

## Documentation

- `docs/index.md` - Usage
- `docs/api.md` - API Reference
- `docs/vision.md` - Vision example
- `docs/tutorial.md` - Tutorial index
