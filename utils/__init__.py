"""Shared utilities for API services.

Exports a simple config helper and a minimal logging helper. Logging will
auto-configure from ``config/logging.yaml`` when present, otherwise it falls
back to a console JSON formatter.
"""

from .config import load_config_file, load_settings, config
from .logger import setup_logging, get_logger, logger


def init_utils(config_dir: str = "config") -> None:
    """Load config from ``config_dir`` then initialize logging once."""
    config.config_dir = config_dir
    config.reload()
    logging_config = config.get("logging", {})
    setup_logging(logging_config=logging_config, config_dir=config_dir)


__all__ = [
    "load_config_file",
    "load_settings",
    "setup_logging",
    "get_logger",
    "logger",
    "config",
    "init_utils",
]
