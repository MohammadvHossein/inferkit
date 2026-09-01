import base64
import json
import logging
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings
from .logging import LoggingMiddleware, logger, setup_logging
from .registry import call_run, call_stream, get_run, get_stream, has_run

limiter = Limiter(key_func=get_remote_address)

async def verify_api_key(x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

def create_app() -> FastAPI:
    setup_logging(logging.INFO if not settings.debug else logging.DEBUG)
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.state.limiter = limiter
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root():
        return {"message": f"Welcome to {settings.app_name}", "docs": "/docs", "has_model": has_run()}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return {"requests": "ok", "model_loaded": has_run()}

    @app.get(f"{settings.api_prefix}/info")
    def info():
        fn = get_run()
        return {"has_model": fn is not None, "model": getattr(fn, "__name__", None) if fn else None}

    def check_size(files: list[UploadFile] | None):
        if not files:
            return
        max_b = settings.max_upload_mb * 1024 * 1024
        for f in files:
            if f.size and f.size > max_b:
                raise HTTPException(status_code=413, detail=f"File too large > {settings.max_upload_mb}MB")

    @app.post(f"{settings.api_prefix}/infer", dependencies=[Depends(verify_api_key)])
    @limiter.limit(settings.rate_limit)
    async def infer(request: Request, payload: str = Form(default="{}"), files: list[UploadFile] | None = File(default=None)):
        try:
            data: dict[str, Any] = json.loads(payload) if payload else {}
        except Exception:
            return JSONResponse({"error": "Invalid JSON in payload"}, status_code=400)
        check_size(files)
        fb = [await f.read() for f in files] if files else None
        if not has_run():
            return JSONResponse({"error": "No model registered. Use @infer"}, status_code=500)
        try:
            result = await call_run(data, fb)
        except Exception as e:
            logger.exception("infer failed")
            return JSONResponse({"error": "inference failed" if not settings.debug else str(e)}, status_code=500)
        if isinstance(result, dict) and "image_base64" in result:
            return result
        if isinstance(result, bytes):
            return Response(content=result, media_type="image/png")
        return result

    @app.post(f"{settings.api_prefix}/infer/json", dependencies=[Depends(verify_api_key)])
    @limiter.limit(settings.rate_limit)
    async def infer_json(request: Request, payload: dict[str, Any]):
        if not has_run():
            return JSONResponse({"error": "No model registered"}, status_code=500)
        try:
            result = await call_run(payload)
        except Exception as e:
            logger.exception("infer_json failed")
            return JSONResponse({"error": "inference failed" if not settings.debug else str(e)}, status_code=500)
        if isinstance(result, dict) and "image_base64" in result:
            return result
        if isinstance(result, bytes):
            return Response(content=result, media_type="image/png")
        return result

    @app.post(f"{settings.api_prefix}/infer/stream", dependencies=[Depends(verify_api_key)])
    @limiter.limit(settings.rate_limit)
    async def infer_stream(request: Request, payload: dict[str, Any]):
        sfn = get_stream()
        if not sfn:
            async def single():
                r = await call_run(payload)
                yield f"data: {json.dumps(r)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(single(), media_type="text/event-stream")
        async def gen():
            async for chunk in call_stream(payload):
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.websocket("/ws/infer")
    @app.websocket(f"{settings.api_prefix}/ws/infer")
    async def ws_infer(ws: WebSocket):
        await ws.accept()
        sfn = get_stream()
        try:
            while True:
                msg = await ws.receive_text()
                try:
                    data = json.loads(msg)
                except Exception:
                    data = {"text": msg}
                if isinstance(data, dict) and data.get("stream") and sfn:
                    async for chunk in call_stream(data):
                        await ws.send_text(json.dumps({"token": chunk}))
                    await ws.send_text(json.dumps({"done": True}))
                    continue
                if not has_run():
                    await ws.send_text(json.dumps({"error": "No model"}))
                    continue
                try:
                    result = await call_run(data)
                    if isinstance(result, bytes):
                        await ws.send_bytes(result)
                    else:
                        await ws.send_text(json.dumps(result, default=str))
                except Exception as e:
                    await ws.send_text(json.dumps({"error": "inference failed" if not settings.debug else str(e)}))
        except WebSocketDisconnect:
            pass

    return app

def serve(entry_file: str | None = None, host: str | None = None, port: int | None = None, reload: bool = False):
    import importlib.util
    import pathlib
    import uvicorn

    if entry_file:
        p = pathlib.Path(entry_file).resolve()
        spec = importlib.util.spec_from_file_location("user_model", str(p))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore

    if not has_run():
        raise RuntimeError("No @infer function found. Decorate your function with @infer")

    app = create_app()
    uvicorn.run(app, host=host or settings.host, port=port or settings.port, reload=reload)
