"""Text chunking for myAudible.

This module provides the ChunkManager class for splitting extracted text
into semantic chunks for TTS processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from myaudible.exceptions import MyAudibleError

# Global constant for chunk size configuration - easy to adjust
MAX_CHUNK = 800


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    max_chars: int = MAX_CHUNK
    overlap_ratio: float = 0.1


class ChunkManagerError(MyAudibleError):
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
        """
        if not text or not text.strip():
            return []

        # Split at paragraph boundaries first, then further split long paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\n+', text.strip()) if p.strip()]
        if not paragraphs:
            return []

        try:
            import semchunk

            chunks = []
            current_parts: list[str] = []
            current_len = 0

            for para in paragraphs:
                if len(para) > self.max_chars:
                    if current_parts:
                        chunks.append('\n\n'.join(current_parts))
                        current_parts = []
                        current_len = 0
                    sub = semchunk.chunk(para, self.max_chars, len)
                    chunks.extend(c.strip() for c in sub if c.strip())
                else:
                    added_len = len(para) + (2 if current_parts else 0)
                    if current_len + added_len <= self.max_chars:
                        current_parts.append(para)
                        current_len += added_len
                    else:
                        chunks.append('\n\n'.join(current_parts))
                        current_parts = [para]
                        current_len = len(para)

            if current_parts:
                chunks.append('\n\n'.join(current_parts))

        except ImportError:
            chunks = list(paragraphs)

        # Apply overlap: prepend tail of previous chunk to each subsequent chunk
        overlap_chars = int(self.max_chars * self.overlap_ratio)
        if overlap_chars > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                tail = chunks[i - 1][-overlap_chars:]
                overlapped.append(tail + chunks[i])
            chunks = overlapped

        return chunks

    async def add_silence_markers(self, chunks: List[str]) -> List[dict]:
        """Add silence markers between paragraph breaks.

        Args:
            chunks: List of text chunks.

        Returns:
            List of chunk metadata with silence markers.
        """
        if not chunks:
            return []

        markers = []
        for i, chunk in enumerate(chunks):
            marker = {
                "chunk": chunk.strip(),
                "sequence_number": i + 1,
                "has_silence_before": False,
            }
            # Add silence marker for all chunks except the first
            if i > 0 and chunk.strip():
                marker["has_silence_before"] = True
            # Preserve paragraph breaks in chunk text
            original_text = chunk.strip()
            if "\n\n" in original_text:
                marker["chunk"] = original_text

            markers.append(marker)

        return markers

    async def calculate_overlap(self) -> int:
        """Calculate overlap size.

        Returns:
            Overlap size in characters.
        """
        overlap_size = int(self.max_chars * self.overlap_ratio)
        return overlap_size

    async def _chunk_fallback(self, text: str) -> List[str]:
        """Fallback to paragraph-based chunking when semchunk unavailable.

        Args:
            text: Text to chunk.

        Returns:
            List of text chunks.
        """
        # Split by paragraph breaks
        paragraphs = text.split('\n\n')
        chunks = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Split paragraph into chunks if too long
            if len(para) > self.max_chars:
                # Simple character-based splitting for long paragraphs
                chunk_size = self.max_chars
                for i in range(0, len(para), chunk_size):
                    chunk = para[i:i + chunk_size]
                    if chunk:
                        chunks.append(chunk)
            else:
                chunks.append(para)

        return chunks
