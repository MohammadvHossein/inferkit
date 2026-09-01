import logging
import sys
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("inferkit")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        try:
            response = await call_next(request)
            duration = (time.time() - start) * 1000
            logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.1f}ms")
            response.headers["X-Response-Time"] = f"{duration:.1f}ms"
            return response
        except Exception as e:
            logger.exception(f"Error {request.url.path}: {e}")
            raise


request_count = 0
