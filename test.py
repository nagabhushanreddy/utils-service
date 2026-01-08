from utils import logger

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

if __name__ == "__main__":
    test_logging()
