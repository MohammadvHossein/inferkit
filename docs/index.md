# InferKit Docs

## نصب
```bash
pip install inferkit              # هسته سبک
pip install inferkit[vision]      # + Pillow
pip install inferkit[torch,transformers]
```

## Text (ساده‌ترین حالت - ۳ خط)
```python
from inferkit import infer
@infer
async def run(payload, files=None):
    return {"output": payload.get("text","")}
# sync هم پشتیبانی می‌شود:
# @infer
# def run(payload): return {"output": "sync"}
```

## Vision (ورودی عکس)
```python
from inferkit import infer
from PIL import Image
import io
@infer
async def run(payload, files=None):
    if not files: return {"error": "no image"}
    img = Image.open(io.BytesIO(files[0]))
    return {"output": f"cat detected {img.size}"}
# کلاینت: curl -F payload='{"text":"hi"}' -F files=@cat.jpg http://localhost:8000/api/v1/infer
```

## Generation (خروجی عکس - پیشنهادی)
```python
from inferkit import infer, image_to_base64
from PIL import Image
@infer
async def run(payload, files=None):
    img = Image.new("RGB", (512,512), "red")
    return image_to_base64(img)  # {"image_base64": ..., "media_type": "image/png"}
# روش دستی قدیمی هم کار می‌کند:
# import base64, io; buf=io.BytesIO(); img.save(buf,format="PNG"); return {"image_base64": base64.b64encode(buf.getvalue()).decode()}
# یا بایت خام: return buf.getvalue()
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
# sync generator هم OK:
# @infer.stream
# def run_stream(payload):
#     for tok in payload["text"].split(): yield tok
```
کلاینت:
- REST SSE: `POST /api/v1/infer/stream` با `{"text":"hello","stream":true}` → `data: {"token": "..."}` + `data: [DONE]`
- WebSocket: `WS /ws/infer` با `{"text":"hi","stream":true}` یا `{"text":"hi"}`

## فایل‌های بزرگ
`.env`: `INFERKIT_MAX_UPLOAD_MB=50` (یا `MAX_UPLOAD_MB`). محدودیت هم روی `Content-Length` و هم `len(bytes)` چک می‌شود، `413` برمی‌گرداند.

## احراز هویت
`.env`: `INFERKIT_API_KEY=secret` → کلاینت `X-API-Key: secret` یا `?api_key=secret` (برای WS)

## تنظیمات (.env)
```
INFERKIT_HOST=0.0.0.0
INFERKIT_PORT=8000
INFERKIT_CORS_ORIGINS=["*"]   # یا * یا http://a.com,http://b.com
INFERKIT_MAX_UPLOAD_MB=50
INFERKIT_RATE_LIMIT=60/minute
INFERKIT_API_KEY=
INFERKIT_DEBUG=false
# نام‌های بدون پیشوند HOST/PORT/... هم برای سازگاری پشتیبانی می‌شود
```

## Optional Deps
```bash
pip install inferkit[vision]        # Pillow
pip install inferkit[torch]         # torch+torchvision
pip install inferkit[transformers]  # transformers+accelerate
pip install inferkit[all]           # همه
pip install inferkit[dev]           # pytest, ruff, mypy
```
