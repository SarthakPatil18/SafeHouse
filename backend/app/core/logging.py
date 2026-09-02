"""Logging configuration and structured HTTP access logging for SafeRoom backend."""

import logging
import sys
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("saferoom")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware logging HTTP requests with structured attributes: path, method, status, latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        path = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code

            # Don't log spam for static files or dashboard pings
            if not path.startswith("/static"):
                logger.info(
                    "HTTP %s %s -> %d (latency: %sms)",
                    method,
                    path,
                    status_code,
                    process_time_ms,
                    extra={
                        "path": path,
                        "method": method,
                        "status_code": status_code,
                        "latency_ms": process_time_ms,
                        "client_ip": request.client.host if request.client else None,
                    },
                )
            return response
        except Exception as e:
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "HTTP %s %s -> Exception: %s (latency: %sms)",
                method,
                path,
                e,
                process_time_ms,
                exc_info=True,
            )
            raise
