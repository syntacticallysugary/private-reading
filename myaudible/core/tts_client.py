"""TTS API client for myAudible.

This module provides the TTSClient class for interfacing with the
Qwen 3.0 TTS API for audio generation.
"""

from __future__ import annotations

import asyncio
import random
from typing import Dict, Optional

from aiohttp import ClientSession
from myaudible.exceptions import TTSAPIError
from myaudible.models import VoiceConfig



class TTSConfig:
    """TTS API configuration."""

    endpoint: str = "http://192.168.1.104:8008/v1/audio/speech"
    retry_attempts: int = 3
    timeout_seconds: int = 600


class TTSClient:
    """Interface with Qwen 3.0 TTS API for audio generation.

    This class provides async HTTP client functionality with retry logic
    and exponential backoff for failed requests.
    """

    def __init__(
        self,
        endpoint: str,
        voice: str = "",
        retry_attempts: int = 3,
        timeout_seconds: int = 600,
    ):
        """Initialize TTSClient.

        Args:
            endpoint: TTS API URL.
            retry_attempts: Maximum retry attempts (default: 3).
            timeout_seconds: Request timeout in seconds.
        """
        self.endpoint = endpoint
        self.voice_design = voice
        self.retry_attempts = retry_attempts
        self.timeout_seconds = timeout_seconds
        self._session: Optional[object] = None

    async def __aenter__(self) -> "TTSClient":
        """Async context manager entry."""
        if self._session is None:
            self._session = ClientSession()
        return self



    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def generate_speech(
        self,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
    ) -> bytes:
        """Generate speech from text with retry logic.

        Args:
            text: Text to convert to speech.
            voice_config: Optional voice configuration.

        Returns:
            Audio data as bytes.

        Raises:
            TTSAPIError: If API call fails.
        """
        if not text.strip():
            raise TTSAPIError("Text is empty or whitespace only")

        attempts = 0
        last_error = None

        while attempts < self.retry_attempts:
            attempts += 1

            try:
                return await self._do_generate(text, voice_config=voice_config)

            except TTSAPIError as e:
                last_error = e

                if attempts < self.retry_attempts:
                    delay = self._calculate_backoff(attempts)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break

        raise last_error or TTSAPIError("Unexpected error occurred")

    async def _do_generate(
        self,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
    ) -> bytes:
        """Perform one TTS HTTP request and return raw WAV bytes."""
        if self._session is None:
            raise TTSAPIError("Session not initialized")

        import aiohttp

        payload: Dict = {
            "input": text,
            "model": "qwen",
            "response_format": "wav",
        }
        if self.voice_design:
            payload["voice_design"] = self.voice_design

        if voice_config:
            if voice_config.ref_audio:
                payload["ref_audio"] = voice_config.ref_audio
            if voice_config.ref_text:
                payload["ref_text"] = voice_config.ref_text
            if voice_config.voice_design:
                payload["voice_design"] = voice_config.voice_design

        try:
            async with self._session.post(
                self.endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
            ) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    raise TTSAPIError(
                        "Rate limited (429)",
                        {"status": 429, "retry_after": retry_after},
                    )
                if response.status >= 400:
                    body = await response.text()
                    raise TTSAPIError(
                        f"TTS API error {response.status}: {body[:200]}",
                        {"status": response.status},
                    )
                return await response.read()
        except TTSAPIError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            msg = str(e) or type(e).__name__
            raise TTSAPIError(f"Network error: {msg}", {"status": 0})


    async def _handle_retry(
        self,
        attempt: int,
        status: int,
        retry_after: Optional[int] = None,
    ) -> None:
        """Handle retryable errors.

        Args:
            attempt: Current attempt number.
            status: HTTP status code.
            retry_after: Optional retry-after value from server.
        """
        if status == 429:
            delay = retry_after or self._calculate_backoff(attempt)
            await asyncio.sleep(delay)
        elif status >= 500:
            delay = self._calculate_backoff(attempt)
            await asyncio.sleep(delay)
        else:
            # Unexpected status code - raise error
            raise TTSAPIError(f"Unexpected status code: {status}")


    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter.

        Args:
            attempt: Current attempt number.

        Returns:
            Backoff delay in seconds.
        """
        base = (2 ** int(attempt)) * 1.0
        jitter = random.uniform(0, 0.5)
        return base + jitter
