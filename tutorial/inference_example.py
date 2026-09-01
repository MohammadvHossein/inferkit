"""
Complete inference file for InferKit - serves checkpoint from train_example
Run: inferkit dev tutorial/inference_example.py
Test: curl -X POST http://localhost:8000/api/v1/infer/json -d '{"features":[5.1,3.5,1.4,0.2]}' -H "Content-Type: application/json"
"""
from pathlib import Path
import pickle
import io
import asyncio
from PIL import Image
from inferkit import infer, image_to_base64

MODEL_PATH = Path("checkpoints/model.pkl")
TARGET_PATH = Path("checkpoints/target_names.pkl")

if MODEL_PATH.exists():
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
        img = Image.open(io.BytesIO(files[0]))
        return {"output": f"image {img.size}", "has_file": True}
    if clf is not None and "features" in payload:
        feats = payload["features"]
        if len(feats) != 4:
            return {"error": "features must be 4 numbers"}
        pred = clf.predict([feats])[0]
        proba = clf.predict_proba([feats])[0].max()
        return {"prediction": int(pred), "label": str(target_names[pred]), "confidence": float(proba)}
    if payload.get("mode") == "image_out":
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
