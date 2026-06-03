"""Data models for Private Reading.

This module defines data classes used throughout the application for
representing processing jobs, audio chunks, and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ProcessingJob:
    """Represents a file processing job."""

    job_id: str
    source_file: Path
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_file: Optional[Path] = None


@dataclass
class AudioChunk:
    """Represents a single audio chunk."""

    chunk_id: str
    text: str
    audio_data: bytes
    duration_ms: int
    sequence_number: int


@dataclass
class ProcessingMetadata:
    """Metadata for processed files."""

    source_file: str
    word_count: int
    chunk_count: int
    total_duration_seconds: float
    voice_config: Dict
    processing_time_seconds: float
    status: str = "completed"


@dataclass
class VoiceConfig:
    """Voice configuration for TTS generation."""

    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None
    voice_design: Optional[str] = None
