"""Shared utilities for API services.

This module provides config and logging utilities with singleton patterns.

**Initialization:**
The logger uses lazy initialization - it's created on first use, not at import time.
This ensures config is loaded before logger is initialized.

**Usage in other services:**

1. Basic usage (config loads automatically):
    from utils import config, logger
    logger.info("Hello", extra={"key": "value"})

2. Explicit initialization order (recommended for services):
    from utils import init_utils
    
    # Initialize in correct order: config first, then logger
    init_utils(config_dir="config")
    
    # Now use them
    from utils import config, logger
    logger.info("Initialized")

3. Multiple services with different configs:
    from utils import config
    
    # Each service sets its config dir
    config.config_dir = "path/to/config"
    config.reload()
    
    # Logger will use the new config on next access
    from utils import logger
    logger.info("Message")
"""

from .config import load_config_file, load_settings, config
from .logger import setup_logging, get_logger, logger, Logger, JsonFormatter, DetailedFormatter


def init_utils(config_dir: str = "config") -> None:
    """Initialize utils in the correct order.
    
    Call this function at application startup to ensure proper initialization:
    1. Config is loaded from the specified directory
    2. Logger is created with config settings
    
    Args:
        config_dir: Directory containing configuration files (YAML/JSON)
        
    Example:
        from utils import init_utils, logger
        
        init_utils(config_dir="config")
        logger.info("Application started")
    """
    # 1. Ensure config is loaded
    config.config_dir = config_dir
    config.reload()
    
    # 2. Initialize logger (will use the loaded config)
    # Access logger to trigger lazy initialization with current config
    _ = logger.info  # This triggers lazy initialization


__all__ = [
    "load_config_file",
    "load_settings",
    "setup_logging",
    "get_logger",
    "logger",
    "Logger",
    "config",
    "JsonFormatter",
    "DetailedFormatter",
    "init_utils",
]
