from loguru import logger
import sys

def configure_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    return logger
