from inferkit import image_to_base64, infer
from PIL import Image


@infer
async def run(payload, files=None):
    text = payload.get("text", "")
    mode = payload.get("mode", "text")

    if files:
        return {"output": f"received {len(files)} file(s)", "text": text}

    if mode == "image_out":
        img = Image.new("RGB", (256, 256), color="blue")
        return image_to_base64(img)

    if mode == "bytes_out":
        img = Image.new("RGB", (64, 64), color="red")
        import io

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    return {"output": f"echo: {text}"}


@infer.stream
async def run_stream(payload):
    import asyncio

    text = payload.get("text", "hello streaming")
    for tok in text.split():
        yield tok + " "
        await asyncio.sleep(0.03)
