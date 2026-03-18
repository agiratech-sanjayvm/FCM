"""
Structured logging configuration for the application.
Uses Python's standard logging with JSON-like structured format.
"""

import logging
import sys


def setup_logger(name: str = "hospital_api") -> logging.Logger:
    """Configure and return a structured logger."""
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on re-import
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        _logger.addHandler(handler)

    return _logger


logger = setup_logger()
