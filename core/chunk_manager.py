"""Text chunking for Private Reading.

This module provides the ChunkManager class for splitting extracted text
into semantic chunks for TTS processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from semchunk import semchunk
    HAS_SEMCUNK = True
except ImportError:
    HAS_SEMCUNK = False
    logging.getLogger(__name__).warning(
        "semchunk not available; falling back to paragraph-based splitting"
    )

from private_reading.exceptions import ChunkingError, PrivateReadingError

# Global constant for chunk size configuration - easy to adjust
MAX_CHUNK = 800


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    max_chars: int = MAX_CHUNK
    overlap_ratio: float = 0.1


class ChunkManagerError(ChunkingError):
    """Raised when chunking fails."""

    pass


class ChunkManager:
    """Split extracted text into semantic chunks using semchunk.

    This class uses semantic-aware chunking to split text into
    paragraph-sized segments suitable for TTS processing.
    """

    def __init__(
        self,
        max_chars: int = MAX_CHUNK,
        overlap_ratio: float = 0.1,
    ):
        """Initialize ChunkManager.

        Args:
            max_chars: Maximum characters per chunk (default: MAX_CHUNK=800).
            overlap_ratio: Overlap percentage (default: 0.1).
        """
        self.max_chars = max_chars
        self.overlap_ratio = overlap_ratio

    async def chunk(self, text: str) -> List[str]:
        """Split text into semantic chunks using semchunk.

        Args:
            text: Text to chunk.

        Returns:
            List of text chunks.

        Raises:
            ChunkManagerError: If chunking fails.
        """
        if not text or not text.strip():
            return []

        try:
            if HAS_SEMCUNK:
                chunks = semchunk(text, self.max_chars)
                return [chunk for chunk in chunks if chunk]
        except Exception as e:
            logging.getLogger(__name__).exception("semchunk failed, falling back to paragraph split")

        # Fallback: paragraph-based splitting
        paragraphs = text.split("\n\n")
        result = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_length = len(para)
            if current_length + para_length <= self.max_chars:
                current_chunk.append(para)
                current_length += para_length
            else:
                if current_chunk:
                    result.append("\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_length

        if current_chunk:
            result.append("\n".join(current_chunk))

        return result

    async def add_silence_markers(self, chunks: List[str]) -> List[dict]:
        """Add silence markers between paragraph breaks.

        Args:
            chunks: List of text chunks.

        Returns:
            List of chunk metadata with silence markers.
        """
        result = []
        for i, chunk in enumerate(chunks):
            has_silence_before = i > 0
            result.append({
                "text": chunk,
                "has_silence_before": has_silence_before,
                "sequence_number": i + 1,
            })
        return result

    def calculate_overlap(self) -> int:
        """Calculate overlap size.

        Returns:
            Overlap size in characters.
        """
        return int(self.max_chars * self.overlap_ratio)
