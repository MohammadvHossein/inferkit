from inferkit import infer
import base64
import io
from PIL import Image

@infer
async def run(payload, files=None):
    text = payload.get("text", "")
    mode = payload.get("mode", "text")

    if files:
        return {"output": f"received {len(files)} file(s)", "text": text}

    if mode == "image_out":
        img = Image.new("RGB", (256, 256), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"image_base64": b64, "media_type": "image/png"}

    return {"output": f"echo: {text}"}

@infer.stream
async def run_stream(payload):
    text = payload.get("text", "hello streaming")
    for tok in text.split():
        yield tok + " "
        import asyncio
        await asyncio.sleep(0.03)
