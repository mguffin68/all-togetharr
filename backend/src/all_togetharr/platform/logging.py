"""Structured JSON logging and request logging middleware."""

import json
import logging
import sys
import time
from datetime import UTC, datetime

from all_togetharr.platform.settings import Settings

_STANDARDS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()) | {
    "message",
    "asctime",
    "color_message",
}

logger = logging.getLogger("all_togetharr.request")


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {}
        for k, v in record.__dict__.items():
            if k not in _STANDARDS:
                obj[k] = v
        obj["time"] = datetime.fromtimestamp(record.created, UTC).isoformat()
        obj["level"] = record.levelname
        obj["logger"] = record.name
        obj["message"] = record.getMessage()
        if record.exc_info and record.exc_info[0] is not None:
            obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(obj, default=str)


def configure_logging(settings: Settings) -> None:
    """Configure the root logger with a JSON handler on stdout."""
    root = logging.getLogger()
    root.handlers[:] = [logging.StreamHandler(sys.stdout)]
    root.handlers[0].setFormatter(_JSONFormatter())
    root.setLevel(settings.log_level)

    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False

    httpx = logging.getLogger("httpx")
    httpx.propagate = True
    httpx.setLevel(logging.WARNING)

    httpcore = logging.getLogger("httpcore")
    httpcore.propagate = True
    httpcore.setLevel(logging.WARNING)


class RequestLoggingMiddleware:
    """ASGI middleware that logs method, path, status and duration."""

    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]
        start = time.perf_counter()
        status = 500

        async def _send(message):
            if message["type"] == "http.response.start":
                nonlocal status
                status = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, _send)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            extra = {"method": method, "path": path, "status": status, "duration_ms": duration_ms}
            if path == "/api/health":
                logger.debug("request complete", extra=extra)
            else:
                logger.info("request complete", extra=extra)
