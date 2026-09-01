import logging
import sys
import time

logger = logging.getLogger("inferkit")
request_count: int = 0
_logging_setup_done = False


def setup_logging(level: int = logging.INFO) -> None:
    global _logging_setup_done
    if _logging_setup_done:
        logger.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    _logging_setup_done = True


class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        start = time.time()
        path = scope.get("path", "")
        method = scope.get("method", "WS")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = (time.time() - start) * 1000
                headers = list(message.get("headers", []))
                headers.append((b"x-response-time", f"{duration:.1f}ms".encode()))
                message["headers"] = headers
                logger.info(f"{method} {path} {message['status']} {duration:.1f}ms")
                global request_count
                request_count += 1
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            if e.__class__.__name__ in ("WebSocketDisconnect", "Disconnect"):
                raise
            logger.exception(f"Error {path}: {e}")
            raise
