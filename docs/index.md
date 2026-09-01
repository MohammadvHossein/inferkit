# InferKit Docs

## Text
```python
from inferkit import infer
@infer
async def run(payload, files=None):
    return {"output": payload["text"]}
```

## Vision (image input)
```python
from inferkit import infer
from PIL import Image
import io
@infer
async def run(payload, files=None):
    img = Image.open(io.BytesIO(files[0]))
    return {"output": "cat detected"}
```

## Generation (image output)
```python
@infer
async def run(payload, files=None):
    import base64, io
    from PIL import Image
    img = Image.new("RGB", (512,512), "red")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return {"image_base64": base64.b64encode(buf.getvalue()).decode()}
```

## Audio
```python
@infer
async def run(payload, files=None):
    audio_bytes = files[0]  # wav/mp3
    return {"transcript": "..."}
```

## LLM Streaming
```python
from inferkit import infer
@infer.stream
async def run_stream(payload):
    for tok in llm.stream(payload["text"]):
        yield tok
```
Client: `POST /api/v1/infer/stream` SSE or `WS /ws/infer` with `{"stream": true}`

## Optional Deps
```bash
pip install inferkit[torch]  # torch+torchvision
pip install inferkit[transformers]
pip install inferkit[dev]
```
