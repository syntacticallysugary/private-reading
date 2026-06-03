"""TTS API client for Private Reading.

This module provides the TTSClient class for interfacing with the
Qwen3-TTS-Base API (OpenAI-compatible /v1/audio/speech) for audio generation.
"""

from __future__ import annotations

import asyncio
import random
from typing import Dict, Optional

from aiohttp import ClientSession
from private_reading.exceptions import TTSAPIError


class TTSClient:
    """Interface with Qwen3-TTS-Base API for audio generation.

    This class provides async HTTP client functionality with retry logic
    and exponential backoff for failed requests.
    """

    def __init__(
        self,
        endpoint: str,
        provider: str = "qwen",
        voice: str = "",
        model: str = "qwen3-tts-base",
        reference_id: str = "",
        temperature: float = 0.9,
        top_p: float = 1.0,
        repetition_penalty: float = 1.05,
        retry_attempts: int = 3,
        timeout_seconds: int = 600,
    ):
        self.endpoint = endpoint
        self.provider = provider
        self.voice = voice
        self.model = model
        self.reference_id = reference_id
        self.temperature = temperature
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty
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

    async def generate_speech(self, text: str) -> bytes:
        """Generate speech from text with retry logic.

        Args:
            text: Text to convert to speech.

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
                return await self._do_generate(text)

            except TTSAPIError as e:
                last_error = e

                if attempts < self.retry_attempts:
                    delay = self._calculate_backoff(attempts)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break

        raise last_error or TTSAPIError("Unexpected error occurred")

    async def _do_generate(self, text: str) -> bytes:
        """Perform one TTS HTTP request and return raw audio bytes."""
        if self._session is None:
            raise TTSAPIError("Session not initialized")

        import aiohttp

        if self.provider == "fish":
            payload: Dict = {
                "text": text,
                "format": "wav",
                "references": [],
                "streaming": False,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "repetition_penalty": self.repetition_penalty,
            }
            if self.reference_id:
                payload["reference_id"] = self.reference_id
        else:  # qwen
            payload = {
                "input": text,
                "model": self.model,
                "response_format": "wav",
                "temperature": self.temperature,
            }
            if self.voice:
                payload["voice"] = self.voice
            elif self.reference_id:
                payload["voice"] = self.reference_id

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
        if status == 429:
            delay = retry_after or self._calculate_backoff(attempt)
            await asyncio.sleep(delay)
        elif status >= 500:
            delay = self._calculate_backoff(attempt)
            await asyncio.sleep(delay)
        else:
            raise TTSAPIError(f"Unexpected status code: {status}")

    def _calculate_backoff(self, attempt: int) -> float:
        base = (2 ** int(attempt)) * 1.0
        jitter = random.uniform(0, 0.5)
        return base + jitter
