"""
Private Reading Logging Configuration Module
======================================

This module provides structured JSON logging configuration for Private Reading.
It supports multiple handlers (console, file, systemd journal) and
configurable log levels.

Usage:
    from private_reading.utils.logging_config import get_logging_config

    config = get_logging_config(log_level="INFO", log_format="json")
    logging_config = config.get_logging_config()
    logging.basicConfig(**logging_config)
"""

import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import python-json-logger for JSON formatting
try:
    import jsonlogger

    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


def _format_json_log_record(record: logging.LogRecord) -> str:
    """
    Format a log record as JSON.

    Args:
        record: The log record to format

    Returns:
        JSON string representation of the log record
    """
    log_data = {
        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
        "module": record.module,
        "function": record.funcName,
        "line": record.lineno,
    }

    # Add extra fields if present
    if hasattr(record, "extra_data"):
        log_data.update(record.extra_data)

    return json.dumps(log_data, default=str)


def get_logging_config(
    log_level: str = "INFO",
    log_format: str = "json",
    console_handler: bool = True,
    file_handler: bool = True,
    max_bytes: int = 10_000_000,  # 10MB
    backup_count: int = 5,
    log_dir: Optional[str] = None,
    enable_json_logger: bool = False,
) -> Dict[str, Any]:
    """
    Get logging configuration dictionary suitable for logging.basicConfig().

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "text")
        console_handler: Whether to include a console (stdout) handler
        file_handler: Whether to include a file handler
        max_bytes: Maximum size for log rotation before rotating
        backup_count: Number of backup log files to keep
        log_dir: Directory for log files (defaults to /opt/private-reading/logs)
        enable_json_logger: Use python-json-logger if available

    Returns:
        Dictionary with logging configuration for basicConfig()
    """
    # Determine log directory
    if log_dir is None:
        # Try standard locations
        log_dir_candidates = [
            "/opt/private-reading/logs",
            Path.home() / ".private_reading" / "logs",
            "./logs",
        ]
        for candidate in log_dir_candidates:
            if candidate == "./logs":
                candidate = Path.cwd() / candidate
            if Path(candidate).exists():
                log_dir = str(candidate)
                break
        else:
            log_dir = "/opt/private-reading/logs"

    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Build formatter
    formatter = None
    if log_format == "json":
        if HAS_JSON_LOGGER and enable_json_logger:
            formatter = jsonlogger.JsonFormatter()
        else:
            # Use custom JSON formatter
            formatter = logging.Formatter(
                fmt="%(timestamp)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S.%f%z",
            )
    else:
        # Standard text format
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Build handlers
    handlers = []

    # Console handler (stdout)
    if console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # File handler with rotation
    if file_handler:
        file_path = Path(log_dir) / "private_reading.log"
        file_handler = RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Systemd journal handler (if running under systemd)
    if os.environ.get("SYSTEMD_JOURNAL_ENABLED", "false").lower() == "true":
        try:
            import logging.handlers

            journal_handler = logging.handlers.SysLogHandler(
                address="/dev/log", facility=logging.facility.LOG_USER
            )
            journal_handler.setLevel(getattr(logging, log_level.upper()))
            journal_handler.setFormatter(formatter)
            handlers.append(journal_handler)
        except Exception:
            # Journal handler failed, continue with other handlers
            pass

    # Create logger
    logger = logging.getLogger("private_reading")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add our handlers
    for handler in handlers:
        logger.addHandler(handler)

    # Return configuration for basicConfig
    return {
        "level": getattr(logging, log_level.upper()),
        "handlers": handlers,
    }


def initialize_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """
    Initialize logging configuration and return the logger.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "text")
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    config = get_logging_config(
        log_level=log_level,
        log_format=log_format,
        console_handler=True,
        file_handler=True,
        log_dir=log_dir,
    )

    # Apply configuration
    logging_config = config.get("level", logging.INFO)
    logging.basicConfig(level=logging_config)

    return logging.getLogger("private_reading")


# Singleton logger instance
_logger: Optional[logging.Logger] = None


def get_logger(
    name: str = "private_reading",
    log_level: Optional[str] = None,
) -> logging.Logger:
    """
    Get or create a configured logger instance.

    Args:
        name: Logger name
        log_level: Optional log level override

    Returns:
        Configured logger instance
    """
    global _logger

    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.propagate = False

    if log_level is not None:
        _logger.setLevel(getattr(logging, log_level.upper()))

    return _logger
