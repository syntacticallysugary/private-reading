"""Text chunking for Private Reading.

This module provides the ChunkManager class for splitting extracted text
into semantic chunks for TTS processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from private_reading.exceptions import PrivateReadingError

# Global constant for chunk size configuration - easy to adjust
MAX_CHUNK = 800


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    max_chars: int = MAX_CHUNK
    overlap_ratio: float = 0.1


class ChunkManagerError(PrivateReadingError):
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

    # Symbols that TTS models choke on, mapped to spoken equivalents or dropped.
    _SYMBOL_MAP: dict[str, str] = {
        # Math comparison
        "≈": "approximately",
        "≠": "not equal to",
        "≤": "or less",
        "≥": "or more",
        "∞": "infinity",
        # Math operators
        "×": "times",
        "÷": "divided by",
        "±": "plus or minus",
        "−": "-",  # Unicode minus → ASCII hyphen
        "√": "square root of",
        # Arrows
        "→": "to",
        "←": "from",
        "↑": "up",
        "↓": "down",
        "⇒": "implies",
        "⇐": "if",
        # Greek letters common in technical text
        "α": "alpha",
        "β": "beta",
        "γ": "gamma",
        "δ": "delta",
        "ε": "epsilon",
        "λ": "lambda",
        "μ": "mu",
        "π": "pi",
        "σ": "sigma",
        "τ": "tau",
        "φ": "phi",
        "ω": "omega",
        "Δ": "delta",
        "Σ": "sum",
        "Ω": "ohm",
        # Units / typography
        "°": " degrees",
        "℃": " degrees Celsius",
        "℉": " degrees Fahrenheit",
        "…": "...",
        "—": ", ",
        "–": ", ",
        # Smart quotes → ASCII
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        # Currency
        "€": "euros",
        "£": "pounds",
        "¥": "yen",
        # Common fractions
        "½": "one half",
        "⅓": "one third",
        "¼": "one quarter",
        "¾": "three quarters",
        # Misc
        "•": "-",
        "·": " ",
        " ": " ",  # non-breaking space
        "­": "",  # soft hyphen
        "™": "",
        "©": "",
        "®": "",
    }

    @staticmethod
    def _normalize(text: str) -> str:
        """Replace symbols that TTS models can't pronounce with spoken equivalents."""
        for symbol, replacement in ChunkManager._SYMBOL_MAP.items():
            if symbol in text:
                text = text.replace(symbol, replacement)
        # Collapse any double-spaces introduced by replacements
        text = re.sub(r" {2,}", " ", text)
        return text

    @staticmethod
    def _clean(text: str) -> str:
        """Remove PDF artifacts and Project Gutenberg boilerplate."""
        # Project Gutenberg: drop everything up to and including the START marker
        start_match = re.search(
            r"^\*\*\*\s*START OF THE PROJECT GUTENBERG EBOOK[^\n]*\*\*\*",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if start_match:
            text = text[start_match.end() :]
        # Project Gutenberg: drop END marker and everything after
        text = re.sub(
            r"\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK.*",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        # Remaining *** section breaks → paragraph break
        text = re.sub(r"\*{3,}", "\n\n", text)
        # Gutenberg eBook references: [eBook #12345]
        text = re.sub(r"\[\s*eBook\s*#\d+\s*\]", "", text, flags=re.IGNORECASE)
        # Gutenberg header metadata lines (Release date, Language, Credits, etc.)
        text = re.sub(
            r"^(Release date|Language|Original publication|Other information"
            r"|Credits?|Produced by|Transcribed by|Updated editions):[^\n]*$",
            "",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        # Tab-indented lines (Gutenberg italics / synopsis blocks) — strip leading tabs
        text = re.sub(r"^\t+", "", text, flags=re.MULTILINE)
        # Inline citation brackets: [1], [1, 2], [1–3]
        text = re.sub(r"\s*\[\s*\d+(?:\s*[,–\-]\s*\d+)*\s*\]", "", text)
        # Equation numbers: trailing (1), (2), (12) on a line — PDF math artifact
        text = re.sub(r"\s*\(\s*\d{1,3}\s*\)\s*$", "", text, flags=re.MULTILINE)
        # Isolated superscript digits on their own line (e.g. I²R split as "I\n2\nR")
        text = re.sub(r"(?m)^(\d{1})\s*$", "", text)
        # arXiv / DOI identifiers and general URLs
        text = re.sub(r"\barXiv:\S+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bdoi:\S+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
        # Footnote / symbol markers inline (∗ † ‡ § ¶)
        text = re.sub(r"[∗†‡§¶]+", "", text)
        # Unicode superscript digits and letters (¹²³ etc.)
        text = re.sub(r"[²³¹⁰-ⁿ]+", "", text)
        # Lines that are clearly footers or metadata
        cleaned_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append(line)
                continue
            # Standalone page numbers: "42", "- 42 -", "Page 42", "Page 42 of 100"
            if re.fullmatch(
                r"[-–—]?\s*\d{1,4}\s*[-–—]?|page\s+\d+(\s+of\s+\d+)?",
                stripped,
                re.IGNORECASE,
            ):
                continue
            # Short footer-style lines: copyright, journal name, document title repeats
            if len(stripped) <= 80 and re.search(
                r"(©|copyright|\ball rights reserved\b|issn\s*:?\s*\d|"
                r"journal of |proceedings of |conference on |"
                r"preprint\b|corresponding author|received:|accepted:|published:|"
                r"\bdoi\b|\barxiv\b|figure\s+\d|table\s+\d)",
                stripped,
                re.IGNORECASE,
            ):
                continue
            cleaned_lines.append(line)
        text = "\n".join(cleaned_lines)
        # Collapse runs of whitespace left behind
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = ChunkManager._normalize(text)
        return text.strip()

    async def chunk(self, text: str) -> List[str]:
        """Split text into semantic chunks using semchunk.

        Args:
            text: Text to chunk.

        Returns:
            List of text chunks.
        """
        if not text or not text.strip():
            return []

        text = self._clean(text)

        # Split at paragraph boundaries first, then further split long paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text.strip()) if p.strip()]
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
                        chunks.append("\n\n".join(current_parts))
                        current_parts = []
                        current_len = 0
                    sub: list[str] = semchunk.chunk(  # type: ignore[assignment]
                        para, self.max_chars, len
                    )
                    chunks.extend(c.strip() for c in sub if c.strip())
                else:
                    added_len = len(para) + (2 if current_parts else 0)
                    if current_len + added_len <= self.max_chars:
                        current_parts.append(para)
                        current_len += added_len
                    else:
                        chunks.append("\n\n".join(current_parts))
                        current_parts = [para]
                        current_len = len(para)

            if current_parts:
                chunks.append("\n\n".join(current_parts))

        except ImportError:
            chunks = list(paragraphs)

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
        paragraphs = text.split("\n\n")
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
                    chunk = para[i : i + chunk_size]
                    if chunk:
                        chunks.append(chunk)
            else:
                chunks.append(para)

        return chunks
