"""Text extraction for myAudible.

This module provides the TextExtractor class for extracting plain text
from various document formats.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
import pdfplumber

PDF = pdfplumber.open

from myaudible.exceptions import TextExtractionError, UnsupportedFormatError


class TextExtractor:
    """Extract plain text from various document formats.

    Supported formats:
    - .md - Markdown files
    - .pdf - PDF documents
    - .txt - Plain text files
    - .docx - Word documents
    """

    def __init__(self):
        """Initialize TextExtractor with format-specific parsers."""
        self._parsers: dict = {}

    async def extract(self, file_path: Path) -> str:
        """Extract text from file based on extension.

        Args:
            file_path: Path to the file to extract text from.

        Returns:
            Extracted text content.

        Raises:
            TextExtractionError: If extraction fails.
            UnsupportedFormatError: If file format is not supported.
        """
        ext = file_path.suffix.lower()

        if ext == ".md":
            return await self._extract_markdown(file_path)
        elif ext == ".pdf":
            return await self._extract_pdf(file_path)
        elif ext == ".txt":
            return await self._extract_txt(file_path)
        elif ext == ".docx":
            return await self._extract_docx(file_path)
        else:
            raise UnsupportedFormatError(f"Unsupported format: {ext}")

    async def _extract_markdown(self, file_path: Path) -> str:
        """Extract text from markdown, stripping formatting.

        Args:
            file_path: Path to the markdown file.

        Returns:
            Plain text content.
        """
        content = file_path.read_text(encoding="utf-8")
        text = self._strip_markdown(content)
        return text

    @staticmethod
    def _strip_markdown(content: str) -> str:
        # Remove links [text](url) — drop both text and URL
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', '', content)
        # Remove bold **text** (including content)
        content = re.sub(r'\*\*([^*]+)\*\*', '', content)
        # Remove italic *text* (including content, not ** patterns)
        content = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', '', content)
        # Remove code block fences
        content = re.sub(r'```[^\n]*\n?', '', content)
        # Remove inline code backticks
        content = content.replace('`', '')
        # Remove headers at line start
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        # Remove list markers at line start
        content = re.sub(r'^[-*]\s+', '', content, flags=re.MULTILINE)
        # Remove horizontal rules
        content = re.sub(r'^-{3,}$', '', content, flags=re.MULTILINE)
        return content.strip()

    async def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF preserving reading order.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Plain text content.

        Raises:
            TextExtractionError: If PDF extraction fails.
        """
        try:
            text_parts = []
            with PDF(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text.strip())
            return "\n\n".join(text_parts)
        except Exception as e:
            raise TextExtractionError(f"Failed to extract text from PDF: {e}") from e

    async def _extract_txt(self, file_path: Path) -> str:
        """Extract text from plain text file.

        Args:
            file_path: Path to the text file.

        Returns:
            Text content.

        Raises:
            TextExtractionError: If extraction fails.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            return content.strip()
        except UnicodeDecodeError:
            # Try common legacy encodings
            for encoding in ["latin-1", "cp1252"]:
                try:
                    content = file_path.read_text(encoding=encoding)
                    return content.strip()
                except UnicodeDecodeError:
                    continue
            raise TextExtractionError("Failed to decode text file with any supported encoding")
        except Exception as e:
            raise TextExtractionError(f"Failed to extract text: {e}") from e

    async def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX preserving paragraph flow.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Plain text content.

        Raises:
            TextExtractionError: If extraction fails.
        """
        try:
            from docx import Document

            doc = Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise TextExtractionError(f"Failed to extract text from DOCX: {e}") from e
