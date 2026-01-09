"""Simplified logger using python-json-logger.

This module provides logging utilities for applications.
The host application is responsible for configuring logging via init_app_logging().

Usage:
    # In your application startup
    from utils.logger import init_app_logging
    init_app_logging(service_name='my-service')
    
    # In your modules
    from utils import logger
    logger.info('message')
    
    # Or get named loggers
    from utils.logger import get_logger
    db_logger = get_logger('database')
"""

import logging
import logging.config
import logging.handlers
from pathlib import Path

from pythonjsonlogger import jsonlogger

from .config import config


_initialized = False
_service_name = None


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that maps levelname to 'level' and asctime to 'timestamp'."""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if 'levelname' in log_record:
            log_record['level'] = log_record.pop('levelname')
        if 'asctime' in log_record:
            log_record['timestamp'] = log_record.pop('asctime')


def init_app_logging(service_name: str = None, logging_config: dict = None):
    """Initialize application logging. Call this once at application startup.
    
    Args:
        service_name: Name of the service (default: from config.application.name or 'utils-service')
        logging_config: Optional logging configuration dict. If not provided, will use config.get("logging")
    
    Returns:
        Logger instance for the service
    
    Example:
        # Basic usage
        init_app_logging('my-service')
        
        # With custom config
        init_app_logging('my-service', logging_config={'level': 'DEBUG', 'file': 'app.log'})
        
        # Using dictConfig
        init_app_logging('my-service', logging_config={
            'version': 1,
            'handlers': {...},
            'formatters': {...}
        })
    """
    global _initialized, _service_name
    
    # Resolve service name
    if not service_name:
        service_name = config.get("application.name", "utils-service")
    _service_name = service_name
    
    # Get logging configuration
    if logging_config is None:
        logging_config = config.get("logging", {})
    
    # Create log file directory if specified
    log_file = logging_config.get("file") or config.get("paths.logs.file")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Clear existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    
    # If logging_config has 'version' key, it's a dictConfig
    if logging_config.get("version"):
        try:
            logging.config.dictConfig(logging_config)
            _initialized = True
            return logging.getLogger(service_name)
        except Exception as e:
            logging.warning(f"Failed to load logging dictConfig: {e}")
    
    # Fallback: setup JSON formatter with basic config
    log_format = '%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(funcName)s %(lineno)d'
    formatter = CustomJsonFormatter(log_format)
    
    # Get log level
    log_level = logging_config.get("level", "INFO")
    level = getattr(logging, str(log_level).upper(), logging.INFO)
    
    # Setup handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=logging_config.get("max_bytes", 10 * 1024 * 1024),
            backupCount=logging_config.get("backup_count", 5),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    root.setLevel(level)
    for handler in handlers:
        root.addHandler(handler)
    
    _initialized = True
    return logging.getLogger(service_name)


class LazyLoggerProxy:
    """Lazy proxy that returns loggers only after initialization."""
    
    def _get_logger(self):
        """Get the logger, initializing if needed."""
        if not _initialized:
            # If not initialized, return a NullHandler logger that warns once
            logger = logging.getLogger('utils-service-uninitialized')
            if not logger.handlers:
                logger.addHandler(logging.NullHandler())
                import warnings
                warnings.warn(
                    "Logging not initialized. Call init_app_logging() in your application startup.",
                    RuntimeWarning,
                    stacklevel=3
                )
            return logger
        return logging.getLogger(_service_name)
    
    def debug(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 1
        return self._get_logger().debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 1
        return self._get_logger().info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 1
        return self._get_logger().warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 1
        return self._get_logger().error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 1
        return self._get_logger().critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 2
        return self._get_logger().exception(msg, *args, **kwargs)
    
    def log(self, level, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 1)
        kwargs['stacklevel'] += 1
        return self._get_logger().log(level, msg, *args, **kwargs)
    
    def __getattr__(self, name):
        return getattr(self._get_logger(), name)


# Lazy logger - dormant until init_app_logging() is called
logger = LazyLoggerProxy()


def get_logger(name: str = None):
    """Get a logger instance.
    
    Args:
        name: Logger name. If None, returns the main service logger.
              If provided, returns a child logger (e.g., 'my-service.database')
        
    Returns:
        Logger instance
    
    Note:
        Make sure to call init_app_logging() before using loggers.
    """
    if not _initialized:
        import warnings
        warnings.warn(
            "Logging not initialized. Call init_app_logging() in your application startup.",
            RuntimeWarning,
            stacklevel=2
        )
        null_logger = logging.getLogger(f'uninitialized.{name or "default"}')
        null_logger.addHandler(logging.NullHandler())
        return null_logger
    
    if name:
        return logging.getLogger(f'{_service_name}.{name}')
    return logging.getLogger(_service_name)


def reset_logging():
    """Reset logging setup (useful for tests)."""
    global _initialized, _service_name
    _initialized = False
    _service_name = None
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()


__all__ = ['logger', 'get_logger', 'init_app_logging', 'reset_logging']
