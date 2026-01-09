"""Shared utilities for API services.

Exports configuration and logging utilities.
Logging must be initialized by calling init_app_logging() in your application.
"""

from .config import load_config_file, load_settings, config
from .logger import init_app_logging, get_logger, logger


def init_utils(config_dir: str = "config", service_name: str = None) -> None:
    """Initialize utilities: load config and setup logging.
    
    This is a convenience function for applications. You can also call
    config.reload() and init_app_logging() separately if you need more control.
    
    Args:
        config_dir: Directory containing configuration files
        service_name: Service name for logging (default: from config.application.name)
    """
    config.config_dir = config_dir
    config.reload()
    init_app_logging(service_name)


__all__ = [
    "load_config_file",
    "load_settings",
    "init_app_logging",
    "get_logger",
    "logger",
    "config",
    "init_utils",
]
