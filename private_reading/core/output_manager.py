"""Output handling for Private Reading.

This module provides the OutputManager class for managing output file
generation and metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from private_reading.exceptions import OutputError


@dataclass
class OutputMetadata:
    """Metadata for output files."""

    source_file: str
    word_count: int
    chunk_count: int
    total_duration_seconds: float
    voice_config: Dict
    processing_time_seconds: float
    status: str = "completed"


class OutputManager:
    """Manage output file generation and metadata.

    This class handles saving WAV files, generating sidecar JSON
    metadata files, and moving processed files to archive directories.
    """

    def __init__(
        self,
        output_dir: Path,
        processed_dir: Optional[Path] = None,
    ):
        """Initialize OutputManager.

        Args:
            output_dir: Directory for output files.
            processed_dir: Optional directory for archived processed files.
        """
        self.output_dir = output_dir
        self.processed_dir = processed_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.processed_dir is not None:
            self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def save_wav(
        self,
        audio_data: bytes,
        original_name: str,
        timestamp: Optional[datetime] = None,
    ) -> Path:
        """Save WAV file with timestamp.

        Args:
            audio_data: Audio data as bytes.
            original_name: Original filename (without extension).
            timestamp: Optional timestamp for filename.

        Returns:
            Path to saved WAV file.
        """
        if not audio_data:
            raise OutputError("No audio data provided")

        if timestamp is None:
            timestamp = datetime.now()

        filename = f"{original_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"
        wav_path = self.output_dir / filename
        wav_path.write_bytes(audio_data)
        return wav_path

    async def save_sidecar(
        self,
        metadata: Dict,
        output_path: Path,
    ) -> None:
        """Save sidecar JSON metadata file.

        Args:
            metadata: Metadata dictionary.
            output_path: Path to the output WAV file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sidecar_path = output_path.with_stem(f"{output_path.stem}.json")
        sidecar_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    async def move_to_processed(self, file_path: Path) -> None:
        """Move processed file to archive directory.

        Args:
            file_path: Path to file to move.
        """
        if self.processed_dir is None:
            raise OutputError("Processed directory not configured")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        filename = file_path.name
        dest_path = self.processed_dir / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.move(str(file_path), str(dest_path))

    async def save_audio_data(
        self,
        audio_data: bytes,
        metadata: Dict,
        original_name: str,
        timestamp: Optional[datetime] = None,
    ) -> tuple[Path, Path]:
        """Save audio data and metadata.

        Args:
            audio_data: Audio data as bytes.
            metadata: Metadata dictionary.
            original_name: Original filename.
            timestamp: Optional timestamp.

        Returns:
            Tuple of (wav_path, sidecar_path).
        """
        wav_path = await self.save_wav(audio_data, original_name, timestamp)
        await self.save_sidecar(metadata, wav_path)
        return wav_path, wav_path.with_stem(f"{wav_path.stem}.json")
