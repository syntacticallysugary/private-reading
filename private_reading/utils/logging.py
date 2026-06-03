"""Structured logging setup for Private Reading.

This module provides logging configuration using structlog for
structured, JSON-formatted log output.
"""

from __future__ import annotations

import logging
import structlog
from pathlib import Path

from private_reading.config import AppConfig


def setup_logging(config: AppConfig) -> None:
    """Configure structured logging.

    Args:
        config: Application configuration with logging settings.
    """
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)

    if config.logging.format == "json":
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
        )
    else:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(),
            ],
        )


def get_logger(name: str = "private_reading") -> structlog.types.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name.

    Returns:
        Bound logger instance.
    """
    return structlog.get_logger(name)
