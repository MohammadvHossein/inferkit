"""
Complete inference file for InferKit - serves checkpoint from train_example.py
Run: inferkit serve tutorial/inference_example.py --port 8001
Test: curl.exe -X POST http://localhost:8001/api/v1/infer/json -H "Content-Type: application/json" -d "{\"features\":[5.1,3.5,1.4,0.2]}"
Docs: http://localhost:8001/docs

Customization (in code):
  from inferkit.server import create_app
  app = create_app(title="My Iris Service", enable_multipart=False, enable_stream=False, enable_ws=False)
  # then only POST /api/v1/infer/json remains in Swagger
Customization (via .env - easier):
  INFERKIT_APP_NAME=My Iris Service
  INFERKIT_ENABLE_MULTIPART=false
  INFERKIT_ENABLE_STREAM=false
"""
import asyncio
import io
import pickle
from pathlib import Path

from inferkit import image_to_base64, infer

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

MODEL_PATH = Path("checkpoints/model.pkl")
TARGET_PATH = Path("checkpoints/target_names.pkl")

if MODEL_PATH.exists() and TARGET_PATH.exists():
    with open(MODEL_PATH, "rb") as f:
        clf = pickle.load(f)
    with open(TARGET_PATH, "rb") as f:
        target_names = pickle.load(f)
    print(f"Model loaded: {clf}")
else:
    print("Warning: checkpoints/model.pkl not found - run python tutorial/train_example.py first")
    clf = None
    target_names = ["setosa", "versicolor", "virginica"]


@infer
async def run(payload, files=None):
    if files:
        if Image is None:
            return {"error": "Pillow not installed. Install with: pip install inferkit[vision]"}
        img = Image.open(io.BytesIO(files[0]))
        return {"output": f"image {img.size}", "has_file": True}
    if clf is not None and "features" in payload:
        feats = payload["features"]
        if not isinstance(feats, list) or len(feats) != 4:
            return {"error": "features must be a list of 4 numbers"}
        try:
            pred = clf.predict([feats])[0]
            proba = clf.predict_proba([feats])[0].max()
        except Exception as e:
            return {"error": str(e)}
        return {"prediction": int(pred), "label": str(target_names[pred]), "confidence": float(proba)}
    if payload.get("mode") == "image_out":
        if Image is None:
            return {"error": "Pillow not installed. Install with: pip install inferkit[vision]"}
        img = Image.new("RGB", (256, 256), "blue")
        return image_to_base64(img)
    text = payload.get("text", "")
    return {"output": f"echo: {text}", "model": "iris-rf"}


@infer.stream
async def run_stream(payload):
    text = payload.get("text", "hello streaming")
    for tok in text.split():
        yield tok + " "
        await asyncio.sleep(0.02)


# --- Code customization (optional) ---
# Uncomment to set custom Swagger title and hide extra APIs directly in code.
# This overrides .env and is picked up automatically by `inferkit serve`.
# from inferkit.server import create_app
# app = create_app(
#     title="My Iris Service",
#     enable_multipart=False,  # hide POST /api/v1/infer
#     enable_stream=False,     # hide POST /api/v1/infer/stream
#     enable_ws=False,         # hide WS /ws/infer
#     # enable_json=True,      # keep only json
# )
