"""TTS API client for Private Reading.

This module provides the TTSClient class for interfacing with the
Qwen 3.0 TTS API for audio generation.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

from private_reading.exceptions import TTSAPIError
from private_reading.models import VoiceConfig


@dataclass
class TTSConfig:
    """TTS API configuration."""

    endpoint: str = "http://192.168.1.104:8008/v1/audio/speech"
    retry_attempts: int = 3
    timeout_seconds: int = 60


class TTSClient:
    """Interface with Qwen 3.0 TTS API for audio generation.

    This class provides async HTTP client functionality with retry logic
    and exponential backoff for failed requests.
    """

    def __init__(
        self,
        endpoint: str,
        retry_attempts: int = 3,
    ):
        """Initialize TTSClient.

        Args:
            endpoint: TTS API URL.
            retry_attempts: Maximum retry attempts (default: 3).
        """
        self.endpoint = endpoint
        self.retry_attempts = retry_attempts
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "TTSClient":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

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
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return await self._do_generate(text, voice_config)
            except TTSAPIError as e:
                if attempt == self.retry_attempts:
                    raise
                # Handle retryable errors
                if e.status == 429:
                    retry_after = e.details.get("retry_after", 1)
                    logging.getLogger(__name__).info(
                        "Rate limited, waiting %d seconds before retry", retry_after
                    )
                    await asyncio.sleep(retry_after)
                elif 500 <= e.status < 600:
                    backoff = self._calculate_backoff(attempt)
                    logging.getLogger(__name__).info(
                        "Server error, waiting %.2f seconds before retry (attempt %d/%d)",
                        backoff,
                        attempt,
                        self.retry_attempts,
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise

    async def _do_generate(
        self,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
    ) -> bytes:
        """Internal method to generate speech (without retry logic).

        Args:
            text: Text to convert to speech.
            voice_config: Optional voice configuration.

        Returns:
            Audio data as bytes.

        Raises:
            TTSAPIError: If API call fails.
        """
        if not self._session:
            raise TTSAPIError("Session not initialized", {"error": "Call __aenter__ first"})

        payload: Dict = {"text": text}

        if voice_config:
            if voice_config.ref_audio:
                payload["ref_audio"] = voice_config.ref_audio
            if voice_config.ref_text:
                payload["ref_text"] = voice_config.ref_text
            if voice_config.voice_design:
                payload["voice_design"] = voice_config.voice_design

        async with self._session.post(
            self.endpoint, json=payload, timeout=aiohttp.ClientTimeout(total=self._session.timeout.total) if hasattr(self._session, 'timeout') else None
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("audio", b"")

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
            sleep_time = retry_after or 1
            logging.getLogger(__name__).info(
                "Rate limited (status %d), waiting %d seconds", status, sleep_time
            )
            await asyncio.sleep(sleep_time)
        elif 500 <= status < 600:
            sleep_time = self._calculate_backoff(attempt)
            logging.getLogger(__name__).info(
                "Server error (status %d), waiting %.2f seconds", status, sleep_time
            )
            await asyncio.sleep(sleep_time)
        else:
            raise TTSAPIError(f"Unexpected status code: {status}", {"status": status})

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter.

        Args:
            attempt: Current attempt number.

        Returns:
            Backoff delay in seconds.
        """
        base_delay = 2 ** attempt * 1.0
        jitter = random.uniform(0, 0.5)
        return base_delay + jitter
