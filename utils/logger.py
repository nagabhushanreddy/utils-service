"""
Minimal logger setup with dictConfig support.

This module provides a centralized logger that services can import.
It prefers a standard logging.config.dictConfig YAML/JSON under the
`logging` key in config; otherwise it falls back to a sensible default.
"""
import logging
import logging.config
from pathlib import Path
from typing import Any, Dict

from .config import config


def _service_name() -> str:
    return (
        config.get("application.name")
        or config.get("service.name")
        or "utils-service"
    )


def _ensure_log_dirs(logging_cfg: Dict[str, Any]) -> None:
    """Create parent directories for any file handlers defined in config."""
    handlers = logging_cfg.get("handlers", {}) if isinstance(logging_cfg, dict) else {}
    for handler in handlers.values():
        if isinstance(handler, dict):
            filename = handler.get("filename")
            if filename:
                try:
                    Path(filename).parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    # Don't fail logger setup if directory creation fails
                    pass


def _default_logging_dict() -> Dict[str, Any]:
    """Return a simple, working dictConfig with console + file handlers.

    Default output is structured JSON using python-json-logger.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # JSON formatter is the default
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(lineno)d",
            },
            # Keep a simple text formatter available if needed
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "logs/service.log",
                "encoding": "utf-8",
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }


# Helpers for dictConfig robustness
def _resolve_placeholders(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve ${VAR:default} placeholders using environment variables."""
    import os, re
    pattern = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")

    def replace_str(s: str) -> str:
        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            default = m.group(2) if m.group(2) is not None else ""
            return os.environ.get(key, default)
        return pattern.sub(repl, s)

    def walk(v: Any) -> Any:
        if isinstance(v, dict):
            return {k: walk(val) for k, val in v.items()}
        if isinstance(v, list):
            return [walk(i) for i in v]
        if isinstance(v, str):
            replaced = replace_str(v)
            # Coerce plain-digit strings to int for handler args like maxBytes/backupCount
            if replaced.isdigit():
                try:
                    return int(replaced)
                except Exception:
                    return replaced
            return replaced
        return v

    return walk(cfg)


def _normalize_formatter_classes(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Convert formatter 'class' entries to '()' callable format."""
    fmts = cfg.get("formatters")
    if isinstance(fmts, dict):
        for _, fmt in fmts.items():
            if isinstance(fmt, dict) and "class" in fmt and "()" not in fmt:
                fmt["()"] = fmt.pop("class")
    return cfg


# Singleton logger instance (created after init_app_logging is called)
_logger_instance: logging.Logger | None = None

_initialized = False


def _apply_logging_config(cfg: Dict[str, Any]) -> None:
    """Apply logging configuration with safe fallback."""
    if not isinstance(cfg, dict):
        cfg = _default_logging_dict()

    # Resolve env placeholders and normalize formatter definitions
    
    cfg = _resolve_placeholders(cfg)
    cfg = _normalize_formatter_classes(cfg)
    
    _ensure_log_dirs(cfg)

    try:
        if cfg.get("version"):
            logging.config.dictConfig(cfg)
        else:
            logging.config.dictConfig(_default_logging_dict())
    except Exception as e:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logging.getLogger(__name__).warning(
            f"Failed to load logging config, using basic config: {e}"
        )


def init_app_logging(service_name: str | None = None, logging_config: Dict[str, Any] | None = None) -> logging.Logger:
    """Initialize application logging. Call this after config is loaded.
    
    Args:
        service_name: Optional service name (defaults to config value)
        logging_config: Optional logging config dict (defaults to config.get('logging'))
    
    Returns:
        Configured logger instance
    """
    global _logger_instance, _initialized
    
    # Get config from parameter or config system
    cfg = logging_config if isinstance(logging_config, dict) else config.get("logging")
    
    # Apply the configuration
    _apply_logging_config(cfg)
    
    # Create and store the logger singleton
    name = service_name or _service_name()
    _logger_instance = logging.getLogger(name)
    _initialized = True
    
    return _logger_instance


def setup_global_logger() -> logging.Logger:
    """Setup and configure the global logger from configuration.
    
    This is called automatically on first logger access if init_app_logging wasn't called.
    """
    global _logger_instance, _initialized
    
    if not _initialized:
        cfg = config.get("logging")
        _apply_logging_config(cfg)
        _logger_instance = logging.getLogger(_service_name())
        _initialized = True
    
    return _logger_instance


class _LazyLogger:
    """Lazy logger proxy that initializes on first access."""
    
    def __getattr__(self, name):
        if _logger_instance is None:
            setup_global_logger()
        return getattr(_logger_instance, name)
    
    def __call__(self, *args, **kwargs):
        if _logger_instance is None:
            setup_global_logger()
        return _logger_instance(*args, **kwargs)


# Lazy logger instance - auto-initializes on first use
logger = _LazyLogger()


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a named logger instance.
    
    Args:
        name: Optional sub-logger name (e.g., 'database' -> 'service.database')
    
    Returns:
        Logger instance
    """
    if not _initialized:
        setup_global_logger()
    
    base = _service_name()
    return logging.getLogger(f"{base}.{name}" if name else base)


__all__ = ["logger", "get_logger", "init_app_logging", "setup_global_logger"]