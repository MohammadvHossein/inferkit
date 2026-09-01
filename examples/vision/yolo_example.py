from inferkit import infer
import io
from PIL import Image

@infer
async def run(payload, files=None):
    if not files:
        return {"error": "no image"}
    img = Image.open(io.BytesIO(files[0]))
    w, h = img.size
    return {"output": f"image {w}x{h}", "boxes": []}
