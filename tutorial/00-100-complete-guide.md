# InferKit 0 to 100 Complete Guide — From Installation to Production Deployment with Training and Checkpoint

> This guide takes you from zero to a production inference service in 15 minutes. You will train a simple model, save a checkpoint, and serve it with a single `inference` file using InferKit.

---

## Table of Contents
1. [What is InferKit?](#1-what-is-inferkit)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Create a Project with `inferkit init`](#4-create-a-project)
5. [Part A: Train a Simple Model and Save Checkpoint](#5-train-a-model)
6. [Part B: Serve the Model with InferKit (inference file)](#6-serve-the-model)
7. [Local Testing](#7-local-testing)
8. [Connect from Other Services](#8-connect-from-other-services)
9. [Production Deployment](#9-production-deployment)
10. [Environment Configuration (`.env`)](#10-environment-configuration)
11. [Production Checklist](#11-production-checklist)
12. [FAQ](#12-faq)

---

## 1. What is InferKit?

A library to turn **any Python function** into a production API without writing FastAPI:

```python
from inferkit import infer
@infer
async def run(payload, files=None):
    return {"output": "hello"}
# Automatically becomes:
# POST /api/v1/infer (multipart)
# POST /api/v1/infer/json
# POST /api/v1/infer/stream (SSE)
# WS /ws/infer
```

Features: `sync/async` support, file/image/audio, LLM streaming, `rate-limit`, `API_KEY`, `CORS`, `GZip`, `lifespan preload` for heavy models.

---

## 2. Prerequisites

- Python 3.11+
- pip

```bash
python --version  # 3.11+
```

---

## 3. Installation

```bash
# lightweight core (no Pillow)
pip install inferkit

# for images
pip install inferkit[vision]

# for torch/transformers
pip install inferkit[torch,transformers]
pip install inferkit[all]  # all extras

# development
pip install -e ".[dev,vision]"
```

---

## 4. Create a Project

```bash
mkdir my-ai && cd my-ai
pip install inferkit
inferkit init
```

Output:
```
.env.example  # sample config
.env          # active copy
Dockerfile    # for deployment
my_model.py   # ready sample
```

Recommended structure for the full tutorial:

```
my-ai/
├── train.py              # model training
├── checkpoints/
│   └── model.pkl         # checkpoint
├── inference.py          # serving file (instead of my_model.py)
├── requirements.txt
├── .env
└── Dockerfile
```

---

## 5. Train a Model (Part A)

Train a simple Iris classifier with `scikit-learn` and save a checkpoint. See the alternative PyTorch example below.

### 5.1 Install training dependency

```bash
pip install scikit-learn
```

### 5.2 File `train.py`

```python
# train.py
from pathlib import Path
import pickle
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

print("Loading data...")
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training...")
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

acc = accuracy_score(y_test, clf.predict(X_test))
print(f"Accuracy: {acc:.3f}")

# save checkpoint
Path("checkpoints").mkdir(exist_ok=True)
with open("checkpoints/model.pkl", "wb") as f:
    pickle.dump(clf, f)

with open("checkpoints/target_names.pkl", "wb") as f:
    pickle.dump(load_iris().target_names, f)

print("Checkpoint saved to checkpoints/model.pkl")
```

### 5.3 Run

```bash
python train.py
# Accuracy: 1.000
# Checkpoint saved to checkpoints/model.pkl
```

### 5.4 PyTorch Alternative (Optional)

```python
# train_torch.py
import torch, torch.nn as nn
from pathlib import Path
Path("checkpoints").mkdir(exist_ok=True)
model = nn.Sequential(nn.Linear(4, 16), nn.ReLU(), nn.Linear(16, 3))
# ... training loop ...
torch.save(model.state_dict(), "checkpoints/torch_model.pt")
print("saved torch_model.pt")
```

---

## 6. Serve the Model (Part B)

Serve the checkpoint with **a single file**. The filename does not matter — `inference.py`, `my_model.py`, or any name.

### 6.1 File `inference.py` (complete)

```python
# inference.py
from inferkit import infer, image_to_base64
import pickle
from pathlib import Path
import numpy as np
from PIL import Image
import io
import asyncio

# --- 1. Load model once at startup (preload) ---
MODEL_PATH = Path("checkpoints/model.pkl")
TARGET_PATH = Path("checkpoints/target_names.pkl")

with open(MODEL_PATH, "rb") as f:
    clf = pickle.load(f)
with open(TARGET_PATH, "rb") as f:
    target_names = pickle.load(f)

# For heavy models (torch/transformers) use preload:
# def preload():
#     global clf
#     clf = pickle.load(open(MODEL_PATH,"rb"))
# run.preload = preload  # called in lifespan with 120s timeout

print(f"Model loaded: {clf}")

# --- 2. Main inference function ---
@infer
async def run(payload, files=None):
    """
    payload: dict from client
      - {"features": [5.1, 3.5, 1.4, 0.2]}  for tabular
      - {"text": "hello"} for LLM
    files: list[bytes] | None  for image/audio
    """
    # file mode (vision)
    if files:
        img = Image.open(io.BytesIO(files[0]))
        return {"output": f"image {img.size}", "has_file": True}

    # tabular mode (Iris)
    if "features" in payload:
        feats = payload["features"]
        if len(feats) != 4:
            return {"error": "features must be 4 numbers"}
        pred = clf.predict([feats])[0]
        proba = clf.predict_proba([feats])[0].max()
        return {
            "prediction": int(pred),
            "label": str(target_names[pred]),
            "confidence": float(proba)
        }

    # text mode
    text = payload.get("text", "")
    return {"output": f"echo: {text}", "model": "iris-rf"}

# --- 3. (Optional) Streaming for LLM ---
@infer.stream
async def run_stream(payload):
    text = payload.get("text", "hello streaming")
    for tok in text.split():
        yield tok + " "
        await asyncio.sleep(0.02)

# --- 4. (Optional) Image output ---
# @infer
# async def run(payload, files=None):
#     if payload.get("mode") == "image_out":
#         img = Image.new("RGB", (256,256), "blue")
#         return image_to_base64(img)
```

Notes:
- `payload` is always `dict`, `files` is `list[bytes] | None`.
- For heavy models define `preload` to load in `lifespan` with 120s timeout.
- Output can be `dict`, `bytes`, or `{"image_base64": ...}`.

---

## 7. Local Testing

```bash
# method 1: CLI (recommended)
inferkit dev inference.py --port 8000
# or
inferkit serve inference.py --port 8000

# method 2: programmatic
# python -c "from inferkit import serve; serve('inference.py', port=8000)"

# docs:
# http://localhost:8000/docs
# http://localhost:8000/health
# http://localhost:8000/metrics
```

### 7.1 Test with curl

```bash
# JSON
curl -X POST http://localhost:8000/api/v1/infer/json \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
# {"prediction":0,"label":"setosa","confidence":0.98}

# text
curl -X POST http://localhost:8000/api/v1/infer/json \
  -d '{"text":"hello inferkit"}'

# file (image)
curl -X POST http://localhost:8000/api/v1/infer \
  -F payload='{"text":"hi"}' -F files=@cat.jpg

# SSE streaming
curl -N -X POST http://localhost:8000/api/v1/infer/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"hello world"}'
# data: {"token":"hello "}
# data: [DONE]
```

### 7.2 Test with Python

```python
import httpx
r = httpx.post("http://localhost:8000/api/v1/infer/json", json={"features":[5.1,3.5,1.4,0.2]})
print(r.json())
# file
with open("cat.jpg","rb") as f:
    r = httpx.post("http://localhost:8000/api/v1/infer", data={"payload": '{"text":"hi"}'}, files={"files": f})
```

---

## 8. Connect from Other Services

### 8.1 From another Python microservice

```python
# service_b.py
import httpx
def call_inferkit(features):
    resp = httpx.post("http://inferkit:8000/api/v1/infer/json", json={"features": features}, timeout=10)
    resp.raise_for_status()
    return resp.json()["label"]

print(call_inferkit([6.0, 2.2, 4.0, 1.0]))  # versicolor
```

### 8.2 From Node.js

```js
const res = await fetch("http://localhost:8000/api/v1/infer/json", {
  method: "POST",
  headers: {"Content-Type":"application/json"},
  body: JSON.stringify({features:[5.1,3.5,1.4,0.2]})
});
console.log(await res.json());
```

### 8.3 WebSocket (for LLM streaming)

```js
const ws = new WebSocket("ws://localhost:8000/ws/infer");
ws.onopen = () => ws.send(JSON.stringify({text:"hello", stream:true}));
ws.onmessage = (e) => console.log(JSON.parse(e.data)); // {token:"hello "}
```

### 8.4 With Authentication

```bash
# .env: INFERKIT_API_KEY=secret123
curl -H "X-API-Key: secret123" http://localhost:8000/api/v1/infer/json -d '{"text":"hi"}'
# WS: ws://localhost:8000/ws/infer?api_key=secret123
```

---

## 9. Production Deployment

### 9.1 One command (automatic)

```bash
inferkit deploy
# if docker/compose exists -> docker compose up --build -d
# if Dockerfile exists -> docker build/run
# otherwise -> .venv + uvicorn on INFERKIT_HOST:PORT
```

### 9.2 Manual Docker

```dockerfile
# Dockerfile (generated by inferkit init)
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .[vision]
EXPOSE 8000
CMD ["inferkit", "serve", "inference.py"]
```

```bash
docker build -t my-inferkit .
docker run -d -p 8000:8000 --env-file .env my-inferkit
```

### 9.3 docker-compose

```yaml
# docker-compose.yml
services:
  inferkit:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes: ["./checkpoints:/app/checkpoints"]
```

---

## 10. Environment Configuration (`.env`)

```bash
# .env.example generated by inferkit init
INFERKIT_HOST=0.0.0.0
INFERKIT_PORT=8000
INFERKIT_CORS_ORIGINS=["*"]   # or * or http://a.com,http://b.com
INFERKIT_MAX_UPLOAD_MB=50
INFERKIT_RATE_LIMIT=60/minute
INFERKIT_API_KEY=             # if set, X-API-Key required
INFERKIT_DEBUG=false
# plain names HOST/PORT/... also supported for backwards compatibility
```

---

## 11. Production Checklist

- [ ] Copy `checkpoints/` in `Dockerfile` or mount as `volume`
- [ ] Set `INFERKIT_API_KEY`
- [ ] Change `CORS` from `*` to real domain
- [ ] Set `MAX_UPLOAD_MB` and `RATE_LIMIT`
- [ ] Define `run.preload` for heavy models
- [ ] Install `inferkit[vision]` or `torch` in `Dockerfile`
- [ ] Test `curl /health` and `/metrics` before release

---

## 12. FAQ

**Difference between `my_model.py` and `inference.py`?** None - any file with `@infer` can be served. `inference.py` is just a conventional name for the serving phase.

**Large checkpoint?** Mount `/app/checkpoints` as `volume` or load from `S3` in `preload`.

**LLM streaming?** Add `@infer.stream` and client calls `POST /infer/stream` with `SSE` or `WS`.

**Error `PIL not found`?** `pip install inferkit[vision]` or `Pillow`.

**Port already in use?** `INFERKIT_PORT=9000 inferkit dev inference.py`

---

## Appendix: Ready to Copy

```bash
git clone https://github.com/MohammadvHossein/inferkit
cd inferkit
pip install -e ".[dev,vision]"
python tutorial/train_example.py
inferkit dev tutorial/inference_example.py
```

Open an issue if needed: `https://github.com/MohammadvHossein/inferkit/issues`
