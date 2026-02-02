"""Logging configuration for Boltz-2 package.

This module provides a centralized logging configuration that allows users
to control output verbosity through environment variables or programmatic
configuration.

Example:
    Set logging level via environment variable::

        export BOLTZ2_LOG_LEVEL=DEBUG

    Or configure programmatically::

        from boltz2.logging_config import setup_logging
        setup_logging(level="DEBUG")
"""

import logging
import os
import sys
from typing import Optional


# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"

# Package logger
logger = logging.getLogger("boltz2")


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    stream: Optional[object] = None,
) -> logging.Logger:
    """Configure logging for the Boltz-2 package.

    This function sets up the root logger for the boltz2 package. It can be
    called multiple times to reconfigure logging.

    Args:
        level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            If not provided, uses BOLTZ2_LOG_LEVEL environment variable,
            defaulting to INFO.
        format_string: Custom format string for log messages. If not provided,
            uses a simple format for INFO level and detailed format otherwise.
        stream: Output stream for logs. Defaults to sys.stderr.

    Returns:
        The configured logger instance for the boltz2 package.

    Example:
        >>> from boltz2.logging_config import setup_logging
        >>> logger = setup_logging(level="DEBUG")
        >>> logger.debug("This is a debug message")
    """
    # Resolve log level
    if level is None:
        level = os.getenv("BOLTZ2_LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, level, logging.INFO)

    # Choose format based on level
    if format_string is None:
        format_string = SIMPLE_FORMAT if numeric_level >= logging.INFO else DEFAULT_FORMAT

    # Configure the package logger
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(numeric_level)
    handler.setFormatter(logging.Formatter(format_string))

    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance for use within the boltz2 package.

    Args:
        name: Optional sub-logger name. If provided, returns a child logger
            of the main boltz2 logger (e.g., 'boltz2.client').

    Returns:
        A logging.Logger instance configured for the boltz2 package.

    Example:
        >>> from boltz2.logging_config import get_logger
        >>> logger = get_logger("client")
        >>> logger.info("Client initialized")
    """
    if name:
        return logging.getLogger(f"boltz2.{name}")
    return logger


# Initialize logging with defaults on module import
setup_logging()
