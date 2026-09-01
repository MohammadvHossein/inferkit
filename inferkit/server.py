import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import inferkit.logging as logging_module

from .config import settings
from .logging import LoggingMiddleware, logger, setup_logging
from .registry import call_run, call_stream, get_run, get_stream, has_run

limiter = Limiter(key_func=get_remote_address)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/flac", "audio/x-wav"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_AUDIO_TYPES | {"application/octet-stream", "text/plain"}


def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"error": "rate limit exceeded", "detail": str(exc.detail)}, status_code=429)


async def verify_api_key(x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def verify_api_key_ws(websocket: WebSocket):
    if settings.api_key:
        key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key") or websocket.query_params.get("token")
        if key != settings.api_key:
            await websocket.close(code=4401)
            raise WebSocketDisconnect


@asynccontextmanager
async def lifespan(app: FastAPI):
    if has_run():
        for fn in [get_run(), get_stream()]:
            if fn and hasattr(fn, "preload"):
                try:
                    result = fn.preload()  # type: ignore
                    if asyncio.iscoroutine(result):
                        await asyncio.wait_for(result, timeout=120)
                    logger.info(f"model preload done: {getattr(fn, '__name__', 'unknown')}")
                except TimeoutError:
                    logger.warning("preload timed out after 120s")
                except Exception as e:
                    logger.exception(f"preload failed: {e}")
                break
        else:
            logger.info("model ready (lazy load on first request)")
    yield


def create_app() -> FastAPI:
    setup_logging(logging.INFO if not settings.debug else logging.DEBUG)
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]

    allow_credentials = False if settings.cors_origins == ["*"] else True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/")
    def root():
        return {"message": f"Welcome to {settings.app_name}", "docs": "/docs", "has_model": has_run()}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return {"requests": logging_module.request_count, "model_loaded": has_run(), "status": "ok"}

    @app.get(f"{settings.api_prefix}/info")
    def info():
        fn = get_run()
        return {"has_model": fn is not None, "model": getattr(fn, "__name__", None) if fn else None}

    def check_size(request: Request, files: list[UploadFile] | None, file_bytes: list[bytes] | None = None):
        max_b = settings.max_upload_mb * 1024 * 1024
        clen = request.headers.get("content-length")
        if clen:
            try:
                if int(clen) > max_b + 2 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail=f"Request too large > {settings.max_upload_mb}MB")
            except ValueError:
                pass
        if file_bytes is not None:
            for b in file_bytes:
                if len(b) > max_b:
                    raise HTTPException(status_code=413, detail=f"File too large > {settings.max_upload_mb}MB")
        elif files:
            for f in files:
                if f.size is not None and f.size > max_b:
                    raise HTTPException(status_code=413, detail=f"File too large > {settings.max_upload_mb}MB")

    def check_file_types(files: list[UploadFile] | None):
        if not files:
            return
        for f in files:
            ctype = (f.content_type or "").lower()
            if ctype and ctype not in ALLOWED_TYPES and not ctype.startswith("image/") and not ctype.startswith("audio/") and not ctype.startswith("video/"):
                logger.warning(f"unexpected file type: {ctype} for {f.filename}")

    def _format_result(result: Any):
        if isinstance(result, dict) and "image_base64" in result:
            return result
        if isinstance(result, bytes):
            return Response(content=result, media_type="image/png")
        if isinstance(result, Response):
            return result
        if isinstance(result, dict) and "media_type" in result and "data" in result:
            return Response(content=result["data"], media_type=result["media_type"])
        return result

    @app.post(f"{settings.api_prefix}/infer", dependencies=[Depends(verify_api_key)])
    @limiter.limit(settings.rate_limit)
    async def infer(request: Request, payload: str = Form(default="{}"), files: list[UploadFile] | None = File(default=None)):
        try:
            data: dict[str, Any] = json.loads(payload) if payload else {}
        except Exception:
            return JSONResponse({"error": "Invalid JSON in payload"}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"error": "payload must be a JSON object"}, status_code=400)
        if len(payload) > 1 * 1024 * 1024:
            return JSONResponse({"error": "payload too large (max 1MB)"}, status_code=413)
        check_file_types(files)
        fb = [await f.read() for f in files] if files else None
        check_size(request, files, fb)
        if not has_run():
            return JSONResponse({"error": "No model registered. Use @infer"}, status_code=500)
        try:
            result = await call_run(data, fb)
        except TypeError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except Exception as e:
            logger.exception("infer failed")
            return JSONResponse({"error": "inference failed" if not settings.debug else str(e)}, status_code=500)
        if isinstance(result, dict) and result.get("media_type") and "image_base64" in result:
            return result
        return _format_result(result)

    @app.post(f"{settings.api_prefix}/infer/json", dependencies=[Depends(verify_api_key)])
    @limiter.limit(settings.rate_limit)
    async def infer_json(request: Request, payload: dict[str, Any]):
        body_size = len(json.dumps(payload, default=str).encode())
        if body_size > 1 * 1024 * 1024:
            return JSONResponse({"error": "payload too large (max 1MB)"}, status_code=413)
        if not has_run():
            return JSONResponse({"error": "No model registered"}, status_code=500)
        try:
            result = await call_run(payload)
        except TypeError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except Exception as e:
            logger.exception("infer_json failed")
            return JSONResponse({"error": "inference failed" if not settings.debug else str(e)}, status_code=500)
        return _format_result(result)

    @app.post(f"{settings.api_prefix}/infer/stream", dependencies=[Depends(verify_api_key)])
    @limiter.limit(settings.rate_limit)
    async def infer_stream(request: Request, payload: dict[str, Any]):
        body_size = len(json.dumps(payload, default=str).encode())
        if body_size > 1 * 1024 * 1024:
            return JSONResponse({"error": "payload too large"}, status_code=413)
        sfn = get_stream()
        if not sfn:
            try:
                r = await call_run(payload)
            except Exception as e:
                logger.exception("infer_stream fallback failed")
                return JSONResponse({"error": "inference failed" if not settings.debug else str(e)}, status_code=500)

            async def single():
                yield f"data: {json.dumps(r, default=str)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(single(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        else:

            async def gen():
                async for chunk in call_stream(payload):
                    yield f"data: {json.dumps({'token': chunk}, default=str)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    async def _ws_handler(ws: WebSocket):
        await verify_api_key_ws(ws)
        await ws.accept()
        sfn = get_stream()
        try:
            while True:
                msg = await ws.receive_text()
                if len(msg) > 1 * 1024 * 1024:
                    await ws.send_text(json.dumps({"error": "message too large"}))
                    continue
                try:
                    data = json.loads(msg)
                except Exception:
                    data = {"text": msg}
                if isinstance(data, dict) and data.get("stream") and sfn:
                    try:
                        async for chunk in call_stream(data):
                            await ws.send_text(json.dumps({"token": chunk}, default=str))
                        await ws.send_text(json.dumps({"done": True}))
                    except Exception as e:
                        await ws.send_text(json.dumps({"error": "inference failed" if not settings.debug else str(e)}))
                    continue
                if not has_run():
                    await ws.send_text(json.dumps({"error": "No model"}))
                    continue
                try:
                    result = await call_run(data if isinstance(data, dict) else {"text": data})
                    if isinstance(result, bytes):
                        await ws.send_bytes(result)
                    else:
                        await ws.send_text(json.dumps(result, default=str))
                except Exception as e:
                    await ws.send_text(json.dumps({"error": "inference failed" if not settings.debug else str(e)}))
        except WebSocketDisconnect:
            pass

    app.add_api_websocket_route("/ws/infer", _ws_handler)
    app.add_api_websocket_route(f"{settings.api_prefix}/ws/infer", _ws_handler)

    return app


def serve(entry_file: str | None = None, host: str | None = None, port: int | None = None, reload: bool = False):
    import importlib.util
    import pathlib
    import sys

    import uvicorn

    if entry_file:
        p = pathlib.Path(entry_file).resolve()
        if str(p.parent) not in sys.path:
            sys.path.insert(0, str(p.parent))
        spec = importlib.util.spec_from_file_location(p.stem, str(p))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore

    if not has_run():
        raise RuntimeError("No @infer function found. Decorate your function with @infer")

    uvicorn.run("inferkit.server:create_app", factory=True, host=host or settings.host, port=port or settings.port, reload=reload)
