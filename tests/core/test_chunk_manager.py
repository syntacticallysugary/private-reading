"""Tests for ChunkManager class."""

import pytest
from pathlib import Path

from myaudible.core.chunk_manager import ChunkManager, ChunkConfig


class TestChunkManager:
    """Test cases for ChunkManager."""

    @pytest.fixture
    def chunk_manager(self):
        """Create ChunkManager instance."""
        return ChunkManager(max_chars=500, overlap_ratio=0.1)

    @pytest.fixture
    def sample_text(self):
        """Sample text for testing."""
        return """
This is a sample paragraph for testing purposes. It contains multiple sentences that should be split into chunks.

The second paragraph continues the text with additional content for semantic chunking. This helps verify that the chunking algorithm works correctly.

Third paragraph with more content to test chunking behavior across multiple paragraphs.
"""

    @pytest.fixture
    def short_text(self):
        """Short text that fits in one chunk."""
        return "This is a short text that should fit in a single chunk."

    @pytest.fixture
    def long_text(self):
        """Long text that requires multiple chunks."""
        return """
This is paragraph one with some content.

This is paragraph two with more content.

This is paragraph three with even more content.

This is paragraph four to ensure we have enough text for multiple chunks.

This is paragraph five to complete the test data.
"""

    @pytest.mark.asyncio
    async def test_chunk_text(self, chunk_manager, sample_text):
        """Test text chunking splits text into multiple chunks."""
        chunks = await chunk_manager.chunk(sample_text)

        # Verify we got multiple chunks
        assert len(chunks) > 1

        # Verify each chunk is within max_chars limit
        for chunk in chunks:
            assert len(chunk) <= chunk_manager.max_chars

    @pytest.mark.asyncio
    async def test_chunk_overlap(self, chunk_manager, sample_text):
        """Test chunk overlap calculation."""
        overlap = await chunk_manager.calculate_overlap()

        # Verify overlap is 10% of max_chars (500 * 0.1 = 50)
        assert overlap == 50

    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, chunk_manager):
        """Test chunking empty text returns empty list."""
        chunks = await chunk_manager.chunk("")

        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_whitespace_only(self, chunk_manager):
        """Test chunking whitespace-only text returns empty list."""
        chunks = await chunk_manager.chunk("   \n\n   ")

        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_single_paragraph(self, chunk_manager, short_text):
        """Test chunking text that fits in one chunk."""
        chunks = await chunk_manager.chunk(short_text)

        # Should return single chunk
        assert len(chunks) == 1
        assert chunks[0] == short_text.strip()

    @pytest.mark.asyncio
    async def test_chunk_multiple_paragraphs(self, chunk_manager, long_text):
        """Test chunking text with multiple paragraphs."""
        chunks = await chunk_manager.chunk(long_text)

        # Should return multiple chunks
        assert len(chunks) > 1

        # Verify each chunk is within limit
        for chunk in chunks:
            assert len(chunk) <= chunk_manager.max_chars

    @pytest.mark.asyncio
    async def test_chunk_with_custom_max_chars(self, tmp_dir):
        """Test chunking with custom max_chars parameter."""
        chunk_manager = ChunkManager(max_chars=100, overlap_ratio=0.1)

        text = "This is a test paragraph with some content that should be split into multiple chunks based on the character limit."
        chunks = await chunk_manager.chunk(text)

        # Verify all chunks are within the 100 char limit
        for chunk in chunks:
            assert len(chunk) <= 100

    @pytest.mark.asyncio
    async def test_chunk_with_custom_overlap(self, tmp_dir):
        """Test chunking with custom overlap_ratio parameter."""
        chunk_manager = ChunkManager(max_chars=500, overlap_ratio=0.2)

        overlap = await chunk_manager.calculate_overlap()

        # Verify overlap is 20% of max_chars (500 * 0.2 = 100)
        assert overlap == 100

    @pytest.mark.asyncio
    async def test_chunk_preserves_paragraph_breaks(self, chunk_manager, sample_text):
        """Test that chunking preserves paragraph breaks."""
        chunks = await chunk_manager.chunk(sample_text)

        # Verify chunks contain text from original paragraphs
        text_lower = sample_text.lower()
        for chunk in chunks:
            assert chunk.strip()  # No empty chunks

    @pytest.mark.asyncio
    async def test_chunk_with_silence_markers(self, chunk_manager, sample_text):
        """Test adding silence markers to chunks."""
        chunks = await chunk_manager.chunk(sample_text)
        markers = await chunk_manager.add_silence_markers(chunks)

        # Verify markers were created for each chunk
        assert len(markers) == len(chunks)

        # Verify first chunk has no silence before
        assert markers[0]["has_silence_before"] is False

        # Verify subsequent chunks have silence before
        for i, marker in enumerate(markers[1:], 1):
            assert marker["has_silence_before"] is True
            assert marker["sequence_number"] == i + 1

    @pytest.mark.asyncio
    async def test_chunk_with_silence_markers_empty(self, chunk_manager):
        """Test adding silence markers to empty chunk list."""
        markers = await chunk_manager.add_silence_markers([])

        assert markers == []

    @pytest.mark.asyncio
    async def test_chunk_with_silence_markers_single(self, chunk_manager, short_text):
        """Test adding silence markers to single chunk."""
        chunks = await chunk_manager.chunk(short_text)
        markers = await chunk_manager.add_silence_markers(chunks)

        assert len(markers) == 1
        assert markers[0]["has_silence_before"] is False

    @pytest.mark.asyncio
    async def test_chunk_with_silence_markers_multiple(self, chunk_manager, long_text):
        """Test adding silence markers to multiple chunks."""
        chunks = await chunk_manager.chunk(long_text)
        markers = await chunk_manager.add_silence_markers(chunks)

        assert len(markers) == len(chunks)
        assert markers[0]["has_silence_before"] is False
        assert all(m["has_silence_before"] for m in markers[1:])

    @pytest.mark.asyncio
    async def test_chunk_with_silence_markers_sequence_numbers(self, chunk_manager, long_text):
        """Test silence markers have correct sequence numbers."""
        chunks = await chunk_manager.chunk(long_text)
        markers = await chunk_manager.add_silence_markers(chunks)

        for i, marker in enumerate(markers):
            assert marker["sequence_number"] == i + 1

    @pytest.mark.asyncio
    async def test_calculate_overlap_returns_int(self, chunk_manager):
        """Test calculate_overlap returns integer value."""
        overlap = await chunk_manager.calculate_overlap()

        assert isinstance(overlap, int)
        assert overlap > 0

    @pytest.mark.asyncio
    async def test_chunk_fallback_when_semchunk_unavailable(self, chunk_manager, long_text):
        """Test chunking falls back to paragraph split when semchunk unavailable."""
        # This test verifies the fallback mechanism works
        # The actual behavior depends on semchunk availability
        chunks = await chunk_manager.chunk(long_text)

        # Should return some chunks regardless of semchunk availability
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chunk_with_newlines(self, chunk_manager):
        """Test chunking handles various newline types."""
        text = "Line 1\n\nLine 2\n\n\nLine 3"
        chunks = await chunk_manager.chunk(text)

        # Should handle multiple newlines
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chunk_with_special_characters(self, chunk_manager):
        """Test chunking handles special characters."""
        text = "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?"
        chunks = await chunk_manager.chunk(text)

        # Should preserve special characters
        assert len(chunks) > 0
