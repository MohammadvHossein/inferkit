# Vision

This example shows how to handle image input and output.

## Input

```python
from inferkit import infer
from PIL import Image
import io

@infer
async def run(payload, files=None):
    if not files:
        return {"error": "no image"}
    img = Image.open(io.BytesIO(files[0]))
    w, h = img.size
    return {"output": f"image {w}x{h}", "boxes": []}
```

See `examples/vision/yolo_example.py`.

## Output

```python
from inferkit import infer, image_to_base64
from PIL import Image

@infer
async def run(payload, files=None):
    img = Image.new("RGB", (512, 512), "red")
    return image_to_base64(img)
```

Raw bytes are also supported: `return png_bytes`.
