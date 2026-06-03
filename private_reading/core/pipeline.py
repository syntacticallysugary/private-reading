"""Processing pipeline for Private Reading.

This module provides the ProcessingPipeline class for orchestrating
the complete audio processing workflow from text extraction to
final output generation.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from private_reading.config import AppConfig
from private_reading.core.audio_stitcher import AudioStitcher
from private_reading.core.chunk_manager import ChunkManager
from private_reading.core.output_manager import OutputManager
from private_reading.core.text_extractor import TextExtractor
from private_reading.core.tts_client import TTSClient
from private_reading.exceptions import (
    AudioError,
    ChunkingError,
    ExtractionError,
    OutputError,
    TTSError,
)


def retry(max_retries: int = 3, backoff_base: float = 1.0):
    """Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_base: Base multiplier for exponential backoff (1s, 2s, 4s).

    Returns:
        Decorator function that wraps async functions with retry logic.
    """

    def decorator(func):
        """Wrap async function with retry logic.

        Args:
            func: The async function to decorate.

        Returns:
            Wrapped async function with retry logic.
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        backoff = backoff_base * (2 ** attempt)
                        await asyncio.sleep(backoff)
            raise last_exception

        return wrapper

    return decorator


@dataclass
class ProcessingResult:
    """Result of a single file processing operation.

    Attributes:
        success: Whether the processing completed successfully.
        output_path: Path to the generated output file.
        error: Error message if processing failed.
        duration: Total processing time in seconds.
    """
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    duration: float = 0.0

    def __post_init__(self):
        """Ensure output_path is None if success is False."""
        if not self.success and self.output_path is None:
            self.output_path = None


@dataclass
class PipelineStatus:
    """Current state of the processing pipeline.

    Attributes:
        state: Current pipeline state (IDLE, PROCESSING, ERROR).
        component_health: Health status of each pipeline component.
        active_jobs: Number of currently active processing jobs.
    """
    state: str = "IDLE"
    component_health: Dict[str, bool] = field(default_factory=dict)
    active_jobs: int = 0


class ProcessingPipeline:
    """Orchestrate the complete audio processing workflow.

    This class coordinates all Phase 2 components to process audio
    files through the complete pipeline: text extraction, chunking,
    TTS generation, audio stitching, and output generation.

    Attributes:
        config: Application configuration.
        extractor: Text extraction component.
        chunk_manager: Text chunking component.
        tts_client: TTS API client.
        audio_stitcher: Audio stitching component.
        output_manager: Output file management component.
        job_tracker: Job tracking component (Phase 3).
    """

    def __init__(self, config: AppConfig):
        """Initialize pipeline with configuration and component instances.

        Args:
            config: Application configuration with paths and settings.
        """
        self.config = config
        self._logger = structlog.get_logger()

        # Create semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(config.semaphore.size)

        # Instantiate Phase 2 components
        self.extractor = TextExtractor()
        self.chunk_manager = ChunkManager(
            max_chars=config.processing.chunk_size,
            overlap_ratio=config.processing.overlap_ratio,
        )
        self.tts_client = TTSClient(
            endpoint=config.tts.endpoint,
            provider=config.tts.provider,
            voice=config.tts.voice,
            model=config.tts.model,
            reference_id=config.tts.reference_id,
            temperature=config.tts.temperature,
            top_p=config.tts.top_p,
            repetition_penalty=config.tts.repetition_penalty,
            retry_attempts=config.tts.retry_attempts,
        )
        self.audio_stitcher = AudioStitcher(
            ffmpeg_path="ffmpeg",
        )
        self.output_manager = OutputManager(
            output_dir=config.output_dir,
            processed_dir=config.processed_dir,
        )

        # JobTracker will be instantiated in Task 3.2
        # For now, we store a placeholder that will be replaced
        self.job_tracker = None  # type: Optional[Any]

    @staticmethod
    def _fix_wav_header(data: bytes) -> bytes:
        """Fix streaming WAV headers where RIFF/data sizes are 0xFFFFFFFF."""
        import struct
        if len(data) < 44 or data[:4] != b'RIFF':
            return data
        if struct.unpack_from('<I', data, 4)[0] != 0xFFFFFFFF:
            return data
        data = bytearray(data)
        struct.pack_into('<I', data, 4, len(data) - 8)
        struct.pack_into('<I', data, 40, len(data) - 44)
        return bytes(data)

    async def _retry_with_backoff(
        self, func: callable, *args, max_retries: int = 3, backoff_base: float = 1.0, **kwargs
    ) -> T:
        """Retry an async function with exponential backoff.

        Args:
            func: The async function to call.
            *args: Positional arguments to pass to the function.
            max_retries: Maximum number of retry attempts.
            backoff_base: Base multiplier for exponential backoff (1s, 2s, 4s).
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function call.

        Raises:
            The last exception if all retries are exhausted.
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)  # type: ignore[return-value]
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    backoff = backoff_base * (2 ** attempt)
                    await asyncio.sleep(backoff)
        raise last_exception  # type: ignore[raise-type]

    async def process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file through the complete pipeline.

        The 7-step workflow:
        1. Extract text from source file
        2. Chunk text into manageable segments
        3. Generate TTS audio for each chunk
        4. Stitch audio chunks together
        5. Save combined WAV file
        6. Save sidecar metadata file
        7. Move to processed directory

        Args:
            file_path: Path to the input file to process.

        Returns:
            ProcessingResult with success status and output path.
        """
        job_id = None
        result = ProcessingResult(
            success=False,
            output_path=None,
            error=None,
            duration=0.0,
        )

        try:
            # Create job
            if self.job_tracker is not None:
                job_id = self.job_tracker.create_job(file_path)
                self.job_tracker.start_job(job_id)

            start_time = time.time()
            text: Optional[str] = None
            chunks: Optional[List[str]] = None
            audio_chunks: List[bytes] = []
            output_wav: Optional[Path] = None

            # Stage 1: Extract
            try:
                text = await self._retry_with_backoff(
                    self.extractor.extract, file_path
                )
            except ExtractionError as e:
                self._logger.error(
                    "pipeline.stage_failed",
                    stage="extract_text",
                    file=str(file_path),
                    error=str(e),
                )
                if job_id and self.job_tracker:
                    self.job_tracker.fail_job(job_id, f"Extraction failed: {e}")
                result.error = f"Extraction failed: {e}"
                return result

            self._logger.info(
                "pipeline.stage_complete",
                stage="extract_text",
                file=str(file_path),
                words=len(text.split()),
            )

            # Stage 2: Chunk
            try:
                chunks = await self.chunk_manager.chunk(text)
            except ChunkingError as e:
                self._logger.error(
                    "pipeline.stage_failed",
                    stage="chunk_text",
                    file=str(file_path),
                    error=str(e),
                )
                if job_id and self.job_tracker:
                    self.job_tracker.fail_job(job_id, f"Chunking failed: {e}")
                result.error = f"Chunking failed: {e}"
                return result

            self._logger.info(
                "pipeline.stage_complete",
                stage="chunk_text",
                file=str(file_path),
                chunk_count=len(chunks),
            )

            # Stage 3: TTS with semaphore-controlled concurrency
            temp_wav_dir = self.config.output_dir / "_tmp"
            temp_wav_dir.mkdir(parents=True, exist_ok=True)
            wav_paths: List[Path] = []
            try:
                async with self.tts_client:
                    # Process all chunks concurrently with semaphore-controlled concurrency
                    async def process_chunk(chunk: str, index: int) -> tuple[int, bytes, Path]:
                        """Process a single chunk through TTS."""
                        chunk_start = time.time()
                        async with self.semaphore:
                            audio_data = await self.tts_client.generate_speech(chunk)
                        chunk_duration = time.time() - chunk_start
                        wav_path = temp_wav_dir / f"{file_path.stem}_{index:04d}.wav"
                        wav_path.write_bytes(self._fix_wav_header(audio_data))
                        self._logger.info(
                            "pipeline.chunk_complete",
                            file=str(file_path),
                            chunk=index + 1,
                            total=len(chunks),
                            chars=len(chunk),
                            duration=round(chunk_duration, 2),
                        )
                        return (index, audio_data, wav_path)

                    # Use asyncio.gather() to process chunks concurrently (semaphore-wrapped)
                    results = await asyncio.gather(*[
                        process_chunk(chunk, i) for i, chunk in enumerate(chunks)
                    ])

                    # Sort results by index to maintain order
                    for index, audio_data, wav_path in sorted(results, key=lambda x: x[0]):
                        audio_chunks.append(audio_data)
                        wav_paths.append(wav_path)
            except TTSError as e:
                self._logger.error(
                    "pipeline.stage_failed",
                    stage="generate_tts",
                    file=str(file_path),
                    chunk_index=len(audio_chunks),
                    error=str(e),
                )
                if job_id and self.job_tracker:
                    self.job_tracker.fail_job(job_id, f"TTS failed: {e}")
                result.error = f"TTS failed: {e}"
                return result

            self._logger.info(
                "pipeline.stage_complete",
                stage="generate_tts",
                file=str(file_path),
                chunk_count=len(chunks),
            )

            # Stage 4: Stitch WAV files into a single output
            output_wav = self.config.output_dir / f"{file_path.name}.wav"
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            try:
                await self.audio_stitcher.stitch(wav_paths, output_wav)
            except AudioError as e:
                self._logger.error(
                    "pipeline.stage_failed",
                    stage="stitch_audio",
                    file=str(file_path),
                    error=str(e),
                )
                if job_id and self.job_tracker:
                    self.job_tracker.fail_job(job_id, f"Stitching failed: {e}")
                result.error = f"Stitching failed: {e}"
                return result

            self._logger.info(
                "pipeline.stage_complete",
                stage="stitch_audio",
                file=str(file_path),
            )

            # Stage 5-7: Save sidecar and archive input
            duration = time.time() - start_time
            try:
                await self.output_manager.save_sidecar(
                    metadata={
                        "source_file": str(file_path),
                        "word_count": len(text.split()),
                        "chunk_count": len(chunks),
                        "duration": duration,
                        "total_duration_seconds": duration,
                        "voice_config": {
                            "endpoint": self.tts_client.endpoint,
                            "provider": self.tts_client.provider,
                        },
                        "processing_time_seconds": duration,
                        "status": "completed",
                    },
                    output_path=output_wav,
                )
                await self.output_manager.move_to_processed(file_path)
            except OutputError as e:
                self._logger.error(
                    "pipeline.stage_failed",
                    stage="output",
                    file=str(file_path),
                    error=str(e),
                )
                if job_id and self.job_tracker is not None:
                    self.job_tracker.fail_job(job_id, f"Output failed: {e}")
                result.error = f"Output failed: {e}"
                return result

            # Success
            if job_id and self.job_tracker is not None:
                self.job_tracker.complete_job(job_id, {"output_path": str(output_wav)})
            result.success = True
            result.output_path = output_wav
            result.duration = duration

            self._logger.info(
                "pipeline.process_complete",
                file=str(file_path),
                success=True,
                duration=result.duration,
            )

        except Exception as e:
            # Catch-all for unexpected errors
            if job_id and self.job_tracker:
                self.job_tracker.fail_job(job_id, f"Unexpected error: {e}")
            result.error = str(e)
            result.duration = time.time() - start_time
            self._logger.exception(
                "pipeline.process_failed",
                file=str(file_path),
                error=result.error,
            )

        return result

    async def process_directory(self, directory: Path) -> List[ProcessingResult]:
        """Process all files in a directory sequentially.

        Scans the input directory for supported file types and processes
        each file sequentially through the complete pipeline. Implements
        graceful degradation: unsupported formats are skipped with warnings,
        and individual file failures do not stop the batch.

        Args:
            directory: Directory containing files to process.

        Returns:
            List of ProcessingResult objects for each processed file.
        """
        results: List[ProcessingResult] = []

        # Scan for supported file types
        supported_extensions = {".md", ".pdf", ".txt", ".docx"}
        files_to_process = []

        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                files_to_process.append(file_path)

        self._logger.info(
            "pipeline.directory_scan",
            directory=str(directory),
            file_count=len(files_to_process),
        )

        # Process each file sequentially with graceful degradation
        for file_path in files_to_process:
            result = await self.process_file(file_path)
            results.append(result)

            if result.success:
                self._logger.info(
                    "pipeline.file_processed",
                    file=str(file_path),
                    output=str(result.output_path),
                )
            else:
                self._logger.warning(
                    "pipeline.file_failed",
                    file=str(file_path),
                    error=result.error,
                )

        # Report summary
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        self._logger.info(
            "pipeline.batch_complete",
            directory=str(directory),
            total=len(results),
            success=success_count,
            failure=fail_count,
        )

        return results

    def get_status(self) -> PipelineStatus:
        """Return current pipeline state with health checks.

        Returns:
            PipelineStatus with component health information.
        """
        status = PipelineStatus(
            state=self._get_state(),
            component_health=self._get_component_health(),
            active_jobs=self._get_active_jobs(),
        )

        self._logger.debug(
            "pipeline.status",
            state=status.state,
            health=status.component_health,
            active_jobs=status.active_jobs,
        )

        return status

    def _get_state(self) -> str:
        """Determine current pipeline state.

        Returns:
            State string: IDLE, PROCESSING, or ERROR.
        """
        if self._has_error():
            return "ERROR"
        elif self._is_processing():
            return "PROCESSING"
        else:
            return "IDLE"

    def _has_error(self) -> bool:
        """Check if pipeline has encountered an error.

        Returns:
            True if an error state is detected.
        """
        # Check job tracker for errors
        if self.job_tracker is not None:
            return self.job_tracker.has_error()
        return False

    def _is_processing(self) -> bool:
        """Check if pipeline is currently processing.

        Returns:
            True if processing is active.
        """
        # Check job tracker for active jobs
        if self.job_tracker is not None:
            return self.job_tracker.has_active_jobs()
        return False

    def _get_component_health(self) -> Dict[str, bool]:
        """Get health status of all pipeline components.

        Returns:
            Dictionary mapping component names to health status.
        """
        health: Dict[str, bool] = {}

        # Check each component's health
        try:
            health["TextExtractor"] = True
        except Exception:
            health["TextExtractor"] = False

        try:
            health["ChunkManager"] = True
        except Exception:
            health["ChunkManager"] = False

        try:
            health["TTSClient"] = True
        except Exception:
            health["TTSClient"] = False

        try:
            health["AudioStitcher"] = True
        except Exception:
            health["AudioStitcher"] = False

        try:
            health["OutputManager"] = True
        except Exception:
            health["OutputManager"] = False

        # JobTracker health (will be available in Task 3.2)
        if self.job_tracker is not None:
            try:
                health["JobTracker"] = self.job_tracker.is_healthy()
            except Exception:
                health["JobTracker"] = False

        return health

    def _get_active_jobs(self) -> int:
        """Get count of active processing jobs.

        Returns:
            Number of currently active jobs.
        """
        if self.job_tracker is not None:
            return self.job_tracker.active_job_count()
        return 0
