"""
Example: How to use utils-service in another service

This demonstrates the recommended initialization pattern to avoid issues
with config and logger loading order.
"""

# ============================================================================
# APPROACH 1: Simple usage (config auto-loads with defaults)
# ============================================================================
from utils import config, logger

# Logger is lazily initialized when first accessed (now with config loaded)
logger.info("Application started")
config.set("custom_key", "custom_value")


# ============================================================================
# APPROACH 2: Explicit initialization (RECOMMENDED for services)
# ============================================================================
from utils import init_utils, logger as logger2

# Call init_utils first to ensure proper initialization order
init_utils(config_dir="config")

# Now logger is guaranteed to be initialized with loaded config
logger2.info("Service initialized", extra={"service": "my-api"})


# ============================================================================
# APPROACH 3: Custom config directory for each service
# ============================================================================
from utils import config as cfg, Logger

# Set config directory before accessing logger
cfg.config_dir = "services/my-service/config"
cfg.reload()

# Reset logger singleton so it reinitializes with new config
Logger.reset()

# Now get logger - it will initialize with the new config
my_logger = Logger()
my_logger.info("Using custom config directory")


# ============================================================================
# HOW IT WORKS (Lazy Initialization)
# ============================================================================
"""
1. When you import:
   from utils import logger
   
   No logger is created yet - just a proxy object.

2. When you first use it:
   logger.info("message")
   
   The proxy detects the access and triggers _get_or_create_logger()
   which creates the real Logger singleton using current config.

3. The config is already loaded by then because:
   - Config singleton is created at import time (fast, no dependencies)
   - Logger is created only when first used (allows config changes first)

This solves the initialization order problem!
"""


# ============================================================================
# KEY POINTS
# ============================================================================
"""
✅ DO:
- Import utils early in your application
- Initialize with init_utils(config_dir="...") if you need custom config
- Access logger when you need it - it will be ready

✅ DON'T:
- Don't modify config after logger is first accessed
- If you must change config, reset logger: Logger.reset()

✅ BEST PRACTICE:
1. At app startup, call init_utils(config_dir)
2. Then import and use logger/config throughout your app
3. Logger is guaranteed to use the right config

Example service entry point:

    from utils import init_utils, logger

    def main():
        # 1. Initialize utils with config directory
        init_utils(config_dir="config")
        
        # 2. Now logger/config are ready to use
        logger.info("Service starting")
        
        # ... rest of application
        
    if __name__ == "__main__":
        main()
"""
