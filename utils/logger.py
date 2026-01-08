"""Tiny logging helper with config module integration.

Behavior:
- If a logging config dict is provided (or available via utils.config), apply it.
- If that dict is a logging ``dictConfig`` (has ``version``), use it directly.
- Otherwise, fall back to a simple JSON console + optional rotating file handler.
"""

from __future__ import annotations

import json
import logging
import logging.config
import logging.handlers
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


DEFAULT_SERVICE_NAME = "utils-service"
_configured = False
_active_service_name = DEFAULT_SERVICE_NAME


class StructuredFormatter(logging.Formatter):
    """Very small JSON formatter built on stdlib only."""

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
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add default extra fields
        payload.update(self.extra_fields)

        # Capture any custom attributes attached via `extra=`
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in {"name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process"}:
                continue
            payload.setdefault(key, value)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR:default} or ${VAR} in config values."""
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
    
    def replacer(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ""
        return os.getenv(var_name, default_value)
    
    return re.sub(pattern, replacer, value)


def _configure_default(
    service_name: str,
    level: str | int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    extra_fields: Optional[Mapping[str, Any]] = None,
) -> None:
    """Set up console + optional file handler with JSON formatting."""
    formatter = StructuredFormatter(service_name=service_name, extra_fields=extra_fields)
    
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # File handler (if configured)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Also name a service-specific logger for convenience
    logging.getLogger(service_name).setLevel(logging.NOTSET)


def _get_logging_config_from_utils(config_dir: str | Path) -> Dict[str, Any]:
    """Attempt to fetch logging config via utils.config, falling back to file scan."""
    try:
        from .config import config as global_config
        cfg = global_config.get("logging", {})
        if cfg:
            return cfg
        # Fallback: merge all config files from directory
        from .config import load_all_config_files
        merged = load_all_config_files(config_dir)
        return merged.get("logging", {}) if isinstance(merged, dict) else {}
    except Exception:
        return {}


def setup_logging(
    service_name: Optional[str] = None,
    *,
    logging_config: Optional[Dict[str, Any]] = None,
    config_dir: str | Path = "config",
) -> None:
    """Idempotent logger setup.

    Priority:
    1) Explicit ``logging_config`` dict provided by caller
    2) Logging config from utils.config (merged files)
    3) Fallback to basic JSON console/file handler
    """
    global _configured, _active_service_name
    if _configured:
        if logging_config is None:
            return
        reset_logging()

    section = logging_config or _get_logging_config_from_utils(config_dir) or {}
    section = section.get("logging", section) if isinstance(section, dict) else {}

    # Resolve parameters
    resolved_service = service_name or section.get("service_name")
    if resolved_service is None:
        try:
            from .config import config as global_config  # type: ignore

            resolved_service = global_config.get("application.name")
        except Exception:
            resolved_service = None
    resolved_service = resolved_service or DEFAULT_SERVICE_NAME
    resolved_level = section.get("level", logging.INFO)
    log_file = section.get("file")
    if isinstance(log_file, str):
        log_file = _resolve_env_vars(log_file)
    if not log_file:
        try:
            from .config import config as global_config  # type: ignore

            fallback_file = global_config.get("paths.logs.file")
            if fallback_file:
                log_file = fallback_file
        except Exception:
            pass
    max_bytes = section.get("max_bytes", 10 * 1024 * 1024)
    backup_count = section.get("backup_count", 5)
    extra_fields = section.get("extra_fields", {}) if isinstance(section, dict) else {}

    # If dictConfig provided, use it directly
    if isinstance(section, dict) and section.get("version"):
        try:
            logging.config.dictConfig(section)
            svc_logger = logging.getLogger(resolved_service)
            svc_logger.setLevel(logging.NOTSET)
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if handler not in svc_logger.handlers:
                    svc_logger.addHandler(handler)
            svc_logger.propagate = True
            _active_service_name = resolved_service
            _configured = True
            return
        except Exception:
            # Fall back to manual configuration
            pass

    _configure_default(
        resolved_service,
        resolved_level,
        log_file,
        max_bytes,
        backup_count,
        extra_fields,
    )

    _configured = True
    _active_service_name = resolved_service


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger, ensuring configuration is applied once."""
    setup_logging()
    return logging.getLogger(name or _active_service_name)


class _LoggerProxy:
    def __getattr__(self, item):
        logger = get_logger()
        return getattr(logger, item)


# Lazy proxy so imports don't freeze configuration before setup
logger = _LoggerProxy()


def reset_logging() -> None:
    """Reset logging setup (useful for tests)."""
    global _configured, _active_service_name
    _configured = False
    _active_service_name = DEFAULT_SERVICE_NAME
    root = logging.getLogger()
    root.handlers.clear()


__all__ = ["setup_logging", "get_logger", "logger", "StructuredFormatter", "reset_logging"]