"""Structured JSON logging.

``get_logger`` returns a singleton-per-name logger with a JSON
StreamHandler attached exactly once.
"""

import logging
import sys
from pythonjsonlogger import json as json_logger
from app.config import get_settings


def get_logger(name: str) -> logging.Logger:
    """
    Returns a structured JSON logger for the given module name.

    Parameters:
        name: Module or component name (e.g. 'broker_integrations.robinhood')

    Returns:
        logging.Logger configured with JSON formatting
    """
    settings = get_settings()
    logger = logging.getLogger(name)

    if (
        logger.handlers
    ):  # Re-entrant calls must not stack multiple handlers on the same logger
        return logger

    log_level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = json_logger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
