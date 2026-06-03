"""File operations helpers for Private Reading.

This module provides utilities for validating and sanitizing input files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from private_reading.exceptions import UnsupportedFormatError

# Configuration constants
ALLOWED_EXTENSIONS = {".md", ".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file(file_path: Path) -> bool:
    """Validate input file for processing.

    Args:
        file_path: Path to the file to validate.

    Returns:
        True if file is valid.

    Raises:
        UnsupportedFormatError: If file extension is not supported.
        ValueError: If file is too large or path traversal detected.
    """
    # Check extension
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(f"Unsupported file extension: {file_path.suffix}")

    # Check file size
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_path.stat().st_size}")

    # Check for path traversal
    if ".." in file_path.parts:
        raise ValueError("Path traversal detected")

    return True


def sanitize_text(text: str) -> str:
    """Sanitize text to prevent injection attacks.

    Args:
        text: Raw text to sanitize.

    Returns:
        Sanitized text with control characters removed and length limited.
    """
    # Remove control characters except common whitespace
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Limit text length
    if len(text) > 100000:
        text = text[:100000]

    return text


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in bytes.
    """
    return file_path.stat().st_size


def format_file_size(size_bytes: float) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string.
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_extension(file_path: Path) -> str:
    """Get file extension in lowercase.

    Args:
        file_path: Path to the file.

    Returns:
        File extension including the dot.
    """
    return file_path.suffix.lower()


def is_supported_format(file_path: Path) -> bool:
    """Check if file has a supported extension.

    Args:
        file_path: Path to the file.

    Returns:
        True if extension is supported.
    """
    return file_path.suffix.lower() in ALLOWED_EXTENSIONS


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions.

    Returns:
        List of supported extensions.
    """
    return [ext for ext in ALLOWED_EXTENSIONS]
