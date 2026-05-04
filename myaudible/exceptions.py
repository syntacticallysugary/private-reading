"""Custom exception hierarchy for myAudible.

This module defines the exception hierarchy used throughout the myAudible
application for error handling and propagation.
"""

from typing import Optional


class MyAudibleError(Exception):
    """Base exception for all myAudible errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        """Initialize the base exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        return self.message


class ExtractionError(MyAudibleError):
    """Raised when text extraction fails."""

    pass


class TextExtractionError(ExtractionError):
    """Raised when text extraction fails."""

    pass


class UnsupportedFormatError(ExtractionError):
    """Raised when an unsupported file format is encountered."""

    pass


class OutputError(MyAudibleError):
    """Raised when output handling fails."""

    pass


class ChunkingError(MyAudibleError):
    """Raised when text chunking fails."""

    pass


class TTSError(MyAudibleError):
    """Raised when TTS API call fails."""

    pass


class TTSAPIError(TTSError):
    """Raised when TTS API call fails."""

    pass


def get_class() -> type:
    """Get the TTSAPIError class for patching."""
    return TTSAPIError



class AudioError(MyAudibleError):
    """Raised when audio processing fails."""

    pass


class AudioProcessingError(AudioError):
    """Raised when audio processing fails."""

    pass


class OutputError(MyAudibleError):
    """Raised when output/metadata operations fail."""

    pass


class PipelineError(MyAudibleError):
    """Raised when pipeline orchestration fails."""

    pass


class OutputManagerError(MyAudibleError):
    """Raised when output handling fails."""

    pass


class MonitoringError(MyAudibleError):
    """Raised when file monitoring/watching fails."""

    pass


class FileWatcherError(MonitoringError):
    """Raised when file watcher operations fail."""

    pass
