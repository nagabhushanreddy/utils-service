"""
Comprehensive logging configuration and utilities.

This module provides structured logging with:
- JSON and plain text formatters
- File and console handlers
- Configuration-driven setup
- Structured logging with extra fields
- Thread-safe operations
- Log rotation support
"""

from __future__ import annotations

import json
import logging
import logging.config
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:
    from .config import config
except ImportError:
    config = None


# Reserved LogRecord attributes
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
    """JSON log formatter with structured fields and extra attributes.
    
    Outputs logs in JSON format with timestamp, level, logger name,
    service name, and any extra fields passed via `extra=` parameter.
    """

    def __init__(
        self,
        service_name: str = "utils-service",
        extra_fields: Optional[Mapping[str, Any]] = None,
        include_exception: bool = True,
    ):
        """Initialize JSON formatter.
        
        Args:
            service_name: Name of the service for identification
            extra_fields: Default fields to include in every log
            include_exception: Whether to include exception info
        """
        super().__init__()
        self.service_name = service_name
        self.extra_fields = dict(extra_fields or {})
        self.include_exception = include_exception

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        """Format log record as JSON string."""
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
            if key in _RESERVED or key.startswith("_"):
                continue
            payload.setdefault(key, value)

        # Include exception information if present
        if self.include_exception and record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        return json.dumps(payload, ensure_ascii=True)


class DetailedFormatter(logging.Formatter):
    """Detailed plain text formatter with color support (optional)."""
    
    DEFAULT_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s (%(filename)s:%(lineno)d)"
    SIMPLE_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, detailed: bool = True):
        """Initialize formatter.
        
        Args:
            fmt: Custom format string
            datefmt: Date format string
            detailed: Use detailed format with file/line info
        """
        if fmt is None:
            fmt = self.DEFAULT_FORMAT if detailed else self.SIMPLE_FORMAT
        super().__init__(fmt=fmt, datefmt=datefmt)


def setup_logging(
    service_name: str = "utils-service",
    level: str | int = "INFO",
    json_logs: bool = False,
    log_file: Optional[str | Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    extra_fields: Optional[Mapping[str, Any]] = None,
    propagate: bool = False,
    use_config: bool = True,
) -> logging.Logger:
    """Configure and return a comprehensive logger.
    
    Args:
        service_name: Name of the service/logger
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Use JSON formatter instead of plain text
        log_file: Path to log file (enables file logging with rotation)
        max_bytes: Max size of log file before rotation
        backup_count: Number of backup files to keep
        extra_fields: Default fields to include in every log
        propagate: Whether to propagate to parent loggers
        use_config: Try to load configuration from config utility
        
    Returns:
        Configured logger instance
    """
    # Try to read from config if available
    if use_config and config is not None:
        try:
            # Override with config values if not explicitly set
            if isinstance(level, str):
                level = config.get('logging.level', level)
            if log_file is None:
                log_file_path = config.get('logging.file') or config.get('paths.logs.file')
                if log_file_path:
                    log_file = Path(log_file_path)
            
            # Get other config settings
            json_logs = config.get('logging.json_format', json_logs)
            max_bytes = config.get('logging.max_bytes', max_bytes)
            backup_count = config.get('logging.backup_count', backup_count)
            
            # Get service name from config
            service_name = config.get('application.name', service_name)
        except Exception as e:
            # Silently continue if config reading fails
            pass

    # Get or create logger
    logger = logging.getLogger(service_name)
    logger.handlers.clear()
    logger.setLevel(level if isinstance(level, int) else getattr(logging, level.upper(), logging.INFO))
    logger.propagate = propagate

    # Create formatter
    if json_logs:
        formatter: logging.Formatter = JsonFormatter(
            service_name=service_name,
            extra_fields=extra_fields,
        )
    else:
        formatter = DetailedFormatter(detailed=True)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        
        # Use JSON for file logs if requested, otherwise use detailed format
        if json_logs:
            file_handler.setFormatter(JsonFormatter(service_name=service_name, extra_fields=extra_fields))
        else:
            file_handler.setFormatter(DetailedFormatter(detailed=True))
        
        logger.addHandler(file_handler)

    return logger


def setup_global_logger(
    service_name: Optional[str] = None,
    use_dict_config: bool = True,
) -> logging.Logger:
    """Setup global logger using configuration from config utility.
    
    Args:
        service_name: Override service name (defaults to config value)
        use_dict_config: Try to use logging.config.dictConfig if available
        
    Returns:
        Configured global logger
    """
    if config is None:
        return setup_logging(service_name=service_name or "utils-service")
    
    # Get service name from config
    if service_name is None:
        service_name = config.get('application.name', 'utils-service')
    
    # Try to use dictConfig if logging config exists in config
    if use_dict_config:
        logging_config = config.get('logging')
        if isinstance(logging_config, dict) and 'version' in logging_config:
            try:
                logging.config.dictConfig(logging_config)
                return logging.getLogger(service_name)
            except Exception as e:
                # Fall through to manual setup
                pass
    
    # Manual setup using config values
    log_level = config.get('logging.level', 'INFO')
    json_logs = config.get('logging.json_format', False)
    log_file_path = config.get('logging.file') or config.get('paths.logs.file')
    max_bytes = config.get('logging.max_bytes', 10 * 1024 * 1024)
    backup_count = config.get('logging.backup_count', 5)
    
    return setup_logging(
        service_name=service_name,
        level=log_level,
        json_logs=json_logs,
        log_file=log_file_path,
        max_bytes=max_bytes,
        backup_count=backup_count,
        use_config=False,  # Already read config
    )


def get_logger(name: Optional[str] = None, module_name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name. If None, returns root logger.
        module_name: Module name to append to base logger name.
        
    Returns:
        Logger instance
        
    Examples:
        >>> logger = get_logger('myapp')
        >>> logger = get_logger('myapp', 'database')  # Returns 'myapp.database'
    """
    if name is None:
        return logging.getLogger()
    
    if module_name:
        return logging.getLogger(f"{name}.{module_name}")
    
    return logging.getLogger(name)


# Initialize global logger instance
try:
    logger = setup_global_logger()
except Exception as e:
    # Fallback to basic logger if setup fails
    logger = logging.getLogger("utils-service")
    logging.basicConfig(level=logging.INFO)
    logger.warning(f"Failed to setup global logger: {e}")


__all__ = [
    'logger',
    'get_logger',
    'setup_logging',
    'setup_global_logger',
    'JsonFormatter',
    'DetailedFormatter',
]