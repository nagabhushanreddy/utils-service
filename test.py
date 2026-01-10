from utils import logger, init_utils

# Initialize logging at application startup
init_utils('config')

logger.info("Hello from test.py")

def test_logging():
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An exception occurred")

    import utils.config as config
    all_config = config.get_all()
    logger.info(f"All configuration: {all_config}")

if __name__ == "__main__":
    test_logging()
