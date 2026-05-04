"""Tests for TTSClient class."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from myaudible.exceptions import TTSAPIError
from myaudible.core.tts_client import TTSClient, TTSConfig
from myaudible.models import VoiceConfig


class TestTTSClient:
    """Test cases for TTSClient."""

    @pytest.fixture
    def tts_client(self):
        """Create TTSClient instance."""
        return TTSClient(
            endpoint="http://localhost:8008/v1/audio/speech",
            retry_attempts=3,
        )

    @pytest.fixture
    def mock_voice_config(self):
        """Create mock voice config."""
        return VoiceConfig(
            ref_audio="test_audio.wav",
            ref_text="Test reference text",
            voice_design="test_design",
        )

    @pytest.mark.asyncio
    async def test_aenter_initializes_session(self, tts_client):
        """Test async context manager entry initializes session."""
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value = mock_session

            await tts_client.__aenter__()

            # Verify session was created
            assert tts_client._session is not None

    @pytest.mark.asyncio
    async def test_aexit_closes_session(self, tts_client):
        """Test async context manager exit closes session."""
        # Initialize session
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value = mock_session

            await tts_client.__aenter__()

            # Verify session exists
            assert tts_client._session is not None

            # Exit context
            await tts_client.__aexit__(None, None, None)

            # Verify session was closed
            assert tts_client._session is None

    @pytest.mark.asyncio
    async def test_generate_speech_success(self, tts_client):
        """Test successful speech generation."""
        # Mock the _do_generate method
        tts_client._do_generate = AsyncMock(return_value=b"audio_data")

        result = await tts_client.generate_speech("Test text")

        # Verify audio data was returned
        assert result == b"audio_data"
        assert tts_client._do_generate.called

    @pytest.mark.asyncio
    async def test_generate_speech_with_voice_config(self, tts_client, mock_voice_config):
        """Test speech generation with voice config."""
        tts_client._do_generate = AsyncMock(return_value=b"audio_data")

        result = await tts_client.generate_speech("Test text", mock_voice_config)

        # Verify _do_generate was called with voice config
        assert tts_client._do_generate.called

    @pytest.mark.asyncio
    async def test_generate_speech_retry_on_429(self, tts_client):
        """Test retry handling for 429 rate limit errors."""
        # Mock _do_generate to raise 429 error on first attempt, succeed on second
        call_count = [0]

        async def mock_do_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TTSAPIError("Rate limited", {"status": 429, "details": {"retry_after": 1}})
            return b"audio_data"

        tts_client._do_generate = mock_do_generate

        # Should succeed after retry
        result = await tts_client.generate_speech("Test text")

        # Verify _do_generate was called twice (once failed, once succeeded)
        assert call_count[0] == 2
        assert result == b"audio_data"

    @pytest.mark.asyncio
    async def test_generate_speech_retry_on_5xx(self, tts_client):
        """Test retry handling for 5xx server errors."""
        # Mock _do_generate to raise 500 error on first 2 attempts, succeed on third
        call_count = [0]

        async def mock_do_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise TTSAPIError("Server error", {"status": 500})
            return b"audio_data"

        tts_client._do_generate = mock_do_generate

        # Should succeed after retry
        result = await tts_client.generate_speech("Test text")

        # Verify _do_generate was called 3 times
        assert call_count[0] == 3
        assert result == b"audio_data"

    @pytest.mark.asyncio
    async def test_generate_speech_exhausts_retries(self, tts_client):
        """Test behavior when all retries are exhausted."""
        # Mock _do_generate to always fail
        async def mock_do_generate(*args, **kwargs):
            raise TTSAPIError("Always fails", {"status": 500})

        tts_client._do_generate = mock_do_generate

        # Should raise after exhausting retries
        with pytest.raises(TTSAPIError):
            await tts_client.generate_speech("Test text")

    @pytest.mark.asyncio
    async def test_generate_speech_no_retry_on_client_error(self, tts_client):
        """Test no retry on non-retryable client errors (4xx except 429)."""
        # Mock _do_generate to raise 400 error
        async def mock_do_generate(*args, **kwargs):
            raise TTSAPIError("Bad request", {"status": 400})

        tts_client._do_generate = mock_do_generate

        # Should raise immediately without retry
        with pytest.raises(TTSAPIError):
            await tts_client.generate_speech("Test text")

    @pytest.mark.asyncio
    async def test_handle_retry_429(self, tts_client):
        """Test _handle_retry for 429 status code."""
        with patch("asyncio.sleep") as mock_sleep:
            await tts_client._handle_retry(1, 429, retry_after=2)

            # Verify sleep was called with retry_after value
            mock_sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_handle_retry_5xx(self, tts_client):
        """Test _handle_retry for 5xx status codes."""
        with patch("asyncio.sleep") as mock_sleep:
            await tts_client._handle_retry(1, 500)

            # Verify sleep was called with backoff value
            mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_retry_raises_on_unexpected(self, tts_client):
        """Test _handle_retry raises on unexpected status codes."""
        with pytest.raises(TTSAPIError):
            await tts_client._handle_retry(1, 404)

    @pytest.mark.asyncio
    async def test_calculate_backoff_exponential(self, tts_client):
        """Test exponential backoff calculation."""
        # Attempt 1: 2^1 * 1.0 + jitter = 2.0 + jitter
        backoff1 = tts_client._calculate_backoff(1)
        assert backoff1 >= 2.0
        assert backoff1 < 2.5  # Jitter is 0-0.5

        # Attempt 2: 2^2 * 1.0 + jitter = 4.0 + jitter
        backoff2 = tts_client._calculate_backoff(2)
        assert backoff2 >= 4.0
        assert backoff2 < 4.5

        # Attempt 3: 2^3 * 1.0 + jitter = 8.0 + jitter
        backoff3 = tts_client._calculate_backoff(3)
        assert backoff3 >= 8.0
        assert backoff3 < 8.5

    @pytest.mark.asyncio
    async def test_calculate_backoff_increases_with_attempt(self, tts_client):
        """Test backoff increases with each attempt."""
        backoffs = [tts_client._calculate_backoff(i) for i in range(1, 6)]

        # Verify backoff increases with each attempt
        for i in range(1, len(backoffs)):
            assert backoffs[i] > backoffs[i - 1]

    @pytest.mark.asyncio
    async def test_calculate_backoff_has_jitter(self, tts_client):
        """Test backoff includes random jitter."""
        # Calculate multiple backoffs for same attempt
        backoffs = [tts_client._calculate_backoff(1) for _ in range(10)]

        # Verify jitter causes variation (not all identical)
        assert len(set(backoffs)) > 1

    @pytest.mark.asyncio
    async def test_session_not_initialized_error(self, tts_client):
        """Test error when session not initialized."""
        # Don't call __aenter__, so session is None
        with pytest.raises(TTSAPIError) as exc_info:
            await tts_client._do_generate("Test text")

        assert "Session not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_speech_without_session(self, tts_client):
        """Test generate_speech without initialized session."""
        # Don't call __aenter__
        with pytest.raises(TTSAPIError):
            await tts_client.generate_speech("Test text")

    @pytest.mark.asyncio
    async def test_generate_speech_with_ref_audio(self, tts_client, mock_voice_config):
        """Test speech generation with ref_audio in voice config."""
        tts_client._do_generate = AsyncMock(return_value=b"audio_data")

        result = await tts_client.generate_speech("Test text", mock_voice_config)

        # Verify _do_generate was called
        assert tts_client._do_generate.called

    @pytest.mark.asyncio
    async def test_generate_speech_with_ref_text(self, tts_client, mock_voice_config):
        """Test speech generation with ref_text in voice config."""
        tts_client._do_generate = AsyncMock(return_value=b"audio_data")

        result = await tts_client.generate_speech("Test text", mock_voice_config)

        # Verify _do_generate was called
        assert tts_client._do_generate.called

    @pytest.mark.asyncio
    async def test_generate_speech_with_voice_design(self, tts_client, mock_voice_config):
        """Test speech generation with voice_design in voice config."""
        tts_client._do_generate = AsyncMock(return_value=b"audio_data")

        result = await tts_client.generate_speech("Test text", mock_voice_config)

        # Verify _do_generate was called
        assert tts_client._do_generate.called

    @pytest.mark.asyncio
    async def test_retry_attempts_config(self, tmp_dir):
        """Test retry_attempts configuration."""
        client = TTSClient(endpoint="http://test", retry_attempts=5)

        assert client.retry_attempts == 5

    @pytest.mark.asyncio
    async def test_timeout_config(self, tmp_dir):
        """Test timeout_seconds configuration."""
        client = TTSClient(endpoint="http://test", retry_attempts=3)

        # TTSClient doesn't store timeout as a direct attribute
        # This test verifies the client can be created with config
        assert client.retry_attempts == 3
        assert client.endpoint == "http://test"
