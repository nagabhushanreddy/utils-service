"""Structured logging utilities."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional


_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


class JsonFormatter(logging.Formatter):
    """JSON log formatter with optional extra fields."""

    def __init__(self, service_name: str, extra_fields: Optional[Mapping[str, Any]] = None):
        super().__init__()
        self.service_name = service_name
        self.extra_fields = dict(extra_fields or {})

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": self.service_name,
            "message": record.getMessage(),
        }

        payload.update(self.extra_fields)

        # Capture any custom attributes attached via `extra=`
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload.setdefault(key, value)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def setup_logging(
    service_name: str,
    level: str | int = "INFO",
    json_logs: bool = True,
    extra_fields: Optional[Mapping[str, Any]] = None,
    propagate: bool = False,
) -> logging.Logger:
    """Configure and return a logger for a service.

    - Sets a single stdout handler with JSON or plain formatting.
    - Clears existing handlers for the named logger to avoid duplicate logs.
    """

    logger = logging.getLogger(service_name)
    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = propagate

    handler = logging.StreamHandler(sys.stdout)

    if json_logs:
        formatter: logging.Formatter = JsonFormatter(
            service_name=service_name,
            extra_fields=extra_fields,
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
