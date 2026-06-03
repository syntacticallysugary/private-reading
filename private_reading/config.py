"""Configuration classes for Private Reading using Pydantic Settings."""

from pathlib import Path
from typing import Any, Optional

from pydantic_settings import BaseSettings

from private_reading.core.chunk_manager import MAX_CHUNK


class SemaphoreConfig(BaseSettings):
    """Semaphore configuration for concurrency control."""

    size: int = 10

    class Config:
        env_prefix = "SEMAPHORE_"

    def __init__(self, **kwargs: Any) -> None:
        """Validate semaphore size on initialization.

        Args:
            **kwargs: Configuration parameters including size.

        Raises:
            ValueError: If size is outside the valid range 1-50.
        """
        super().__init__(**kwargs)
        if self.size < 1 or self.size > 50:
            raise ValueError(f"Semaphore size must be between 1 and 50, got {self.size}")


class TTSConfig(BaseSettings):
    """TTS API configuration."""

    endpoint: str = "http://localhost:8014/v1/audio/speech"
    provider: str = "qwen"
    voice: str = ""
    model: str = "qwen3-tts-base"
    reference_id: str = ""
    temperature: float = 0.9
    top_p: float = 1.0
    repetition_penalty: float = 1.05
    retry_attempts: int = 3
    base_backoff_ms: int = 1000
    timeout_seconds: int = 120

    class Config:
        env_prefix = "TTS_"


class ProcessingConfig(BaseSettings):
    """Processing configuration."""

    chunk_size: int = MAX_CHUNK
    overlap_ratio: float = 0.1
    max_parallel: int = 2

    class Config:
        env_prefix = "PROCESSING_"


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    output: str = "journald"

    class Config:
        env_prefix = "LOG_"


class AppConfig(BaseSettings):
    """Application configuration."""

    input_dir: Path = Path("/input")
    output_dir: Path = Path("/output")
    processed_dir: Optional[Path] = None
    archive_dir: Optional[Path] = None

    semaphore: SemaphoreConfig
    tts: TTSConfig
    processing: ProcessingConfig
    logging: LoggingConfig

    class Config:
        env_prefix = "APP_"

    @property
    def tts_endpoint(self) -> str:
        """Get TTS endpoint."""
        return self.tts.endpoint

    @property
    def chunk_size(self) -> int:
        """Get chunk size."""
        return self.processing.chunk_size

    @property
    def max_parallel(self) -> int:
        """Get maximum parallel processing."""
        return self.processing.max_parallel

    @property
    def log_level(self) -> str:
        """Get log level."""
        return self.logging.level

    @property
    def semaphore_size(self) -> int:
        """Get semaphore size for concurrency control."""
        return self.semaphore.size

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value by key.

        Args:
            key: Configuration key (e.g., "watch_mode", "single_file").
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        mapping = {
            "watch_mode": self.processing.max_parallel == 0,
            "single_file": None,
            "version": "1.0.0",
        }
        return mapping.get(key, default)
