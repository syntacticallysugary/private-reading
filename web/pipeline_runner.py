"""Orchestrates the text-to-WAV pipeline for web-submitted jobs.

Wires together ChunkManager, Fish TTS HTTP calls, and AudioStitcher.
Uses the Fish TTS API payload format documented in fishChanges.md.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

import aiohttp

from core.audio_stitcher import AudioStitcher
from core.chunk_manager import ChunkManager
from private_reading.config import ProcessingConfig, SemaphoreConfig, TTSConfig


async def run_pipeline(
    text: str,
    output_dir: Path,
    job_id: str,
    tts: TTSConfig,
    processing: ProcessingConfig,
    semaphore: SemaphoreConfig,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Convert plain text to a WAV file via the Fish TTS server.

    Args:
        text: Input text to convert to audio.
        output_dir: Directory where the final WAV and temp files are written.
        job_id: Unique identifier for this job (used for filenames).
        tts: TTS server configuration (endpoint, voice params, retry policy).
        processing: Chunking configuration (chunk size, overlap ratio).
        semaphore: Concurrency configuration (max parallel TTS requests).
        on_progress: Optional callback invoked with (chunks_done, chunks_total)
            after each chunk completes.

    Returns:
        Path to the finished WAV file.

    Raises:
        ValueError: If the text produces no processable chunks.
        aiohttp.ClientError: If TTS requests fail after all retries.
        AudioProcessingError: If ffmpeg stitching fails.
    """
    chunks = await ChunkManager(
        max_chars=processing.chunk_size,
        overlap_ratio=processing.overlap_ratio,
    ).chunk(text)

    if not chunks:
        raise ValueError("Text produced no processable chunks after splitting.")

    total = len(chunks)
    if on_progress:
        on_progress(0, total)

    tmp_dir = output_dir / f".tmp_{job_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(semaphore.size)
    done_count = 0

    timeout = aiohttp.ClientTimeout(total=120)

    async def _generate_chunk(index: int, chunk_text: str, session: aiohttp.ClientSession) -> Path:
        nonlocal done_count

        payload: dict = {
            "text": chunk_text,
            "format": "wav",
            "references": [],
            "streaming": False,
            "temperature": tts.temperature,
            "top_p": tts.top_p,
            "repetition_penalty": tts.repetition_penalty,
        }
        if tts.reference_id:
            payload["reference_id"] = tts.reference_id

        async with sem:
            last_exc: Exception | None = None
            for attempt in range(1, tts.retry_attempts + 1):
                try:
                    async with session.post(tts.endpoint, json=payload) as resp:
                        resp.raise_for_status()
                        audio_bytes = await resp.read()
                    break
                except Exception as exc:
                    last_exc = exc
                    if attempt < tts.retry_attempts:
                        await asyncio.sleep(2 ** attempt)
            else:
                raise last_exc  # type: ignore[misc]

        wav_path = tmp_dir / f"chunk_{index:04d}.wav"
        wav_path.write_bytes(audio_bytes)

        done_count += 1
        if on_progress:
            on_progress(done_count, total)

        return wav_path

    async with aiohttp.ClientSession(timeout=timeout) as session:
        wav_paths: list[Path] = list(
            await asyncio.gather(
                *[_generate_chunk(i, chunk, session) for i, chunk in enumerate(chunks)]
            )
        )

    sorted_paths = sorted(wav_paths, key=lambda p: p.name)
    final_wav = output_dir / f"{job_id}.wav"
    await AudioStitcher().stitch(sorted_paths, final_wav, add_silence_between=False)

    for f in tmp_dir.iterdir():
        f.unlink(missing_ok=True)
    tmp_dir.rmdir()

    return final_wav
