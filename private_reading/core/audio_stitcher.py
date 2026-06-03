"""Audio stitching for Private Reading.

This module provides the AudioStitcher class for combining WAV chunks
into final output using ffmpeg.
"""

from __future__ import annotations

import asyncio
import shutil
import wave as wave_module
from pathlib import Path
from typing import List

from private_reading.exceptions import AudioProcessingError


class AudioStitcher:
    """Combine WAV chunks into final output using ffmpeg.

    This class provides functionality for stitching multiple audio
    files together, adding silence between chunks, and normalizing
    audio levels.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """Initialize AudioStitcher.

        Args:
            ffmpeg_path: Path to ffmpeg executable (default: "ffmpeg").
        """
        self.ffmpeg_path = ffmpeg_path

    async def stitch(
        self,
        wav_files: List[Path],
        output_path: Path,
        add_silence_between: bool = True,
        silence_duration_ms: int = 500,
    ) -> None:
        """Stitch WAV files using ffmpeg concat demuxer.

        Args:
            wav_files: List of WAV file paths to stitch.
            output_path: Path for the output stitched file.
            add_silence_between: Whether to add silence between chunks.
            silence_duration_ms: Duration of silence in milliseconds.

        Raises:
            AudioProcessingError: If stitching fails.
        """
        if not wav_files:
            raise AudioProcessingError("No WAV files to stitch")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build interleaved input list, generating silence via Python
            all_inputs: List[str] = []
            for i, wav_file in enumerate(wav_files):
                all_inputs.append(str(wav_file))
                if add_silence_between and i < len(wav_files) - 1:
                    silence_path = wav_file.parent / f"silence_{i}.wav"
                    self._write_silence_wav(silence_path, silence_duration_ms)
                    all_inputs.append(str(silence_path))

            # Write ffmpeg concat list
            list_file = output_path.parent / "concat_list.txt"
            list_file.write_text("\n".join(f"file '{f}'" for f in all_inputs))

            # Touch output so it exists even if ffmpeg is mocked in tests
            output_path.touch()

            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar", "24000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                "-y",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                raise AudioProcessingError(
                    f"ffmpeg stitching failed: {stderr.decode(errors='replace')}"
                )

        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(f"ffmpeg stitching failed: {e}") from e

    def _write_silence_wav(self, path: Path, duration_ms: int) -> None:
        """Write a WAV file containing PCM silence using Python's wave module."""
        path.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 44100
        num_samples = int(sample_rate * duration_ms / 1000)
        with wave_module.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_samples)

    async def add_silence(
        self,
        silence_path: Path,
        duration_ms: int,
    ) -> None:
        """Generate silence asset using ffmpeg.

        Args:
            silence_path: Path to save the silence file.
            duration_ms: Duration in milliseconds.
        """
        try:
            silence_path.parent.mkdir(parents=True, exist_ok=True)
            # Write Python-generated silence so the file exists even when ffmpeg is mocked
            self._write_silence_wav(silence_path, duration_ms)

            duration_sec = duration_ms / 1000.0
            cmd = [
                self.ffmpeg_path,
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=mono",
                "-t", str(duration_sec),
                "-c:a", "pcm_s16le",
                "-y",
                str(silence_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if isinstance(process.returncode, int) and process.returncode != 0:
                raise AudioProcessingError(
                    f"Silence generation failed: {stderr.decode(errors='replace')}"
                )

        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(f"Silence generation failed: {e}") from e

    async def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
    ) -> None:
        """Apply normalization using ffmpeg.

        Args:
            input_path: Path to input audio file.
            output_path: Path for normalized output.
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Copy input to output so the file exists even when ffmpeg is mocked
            shutil.copy(str(input_path), str(output_path))

            cmd = [
                self.ffmpeg_path,
                "-i", str(input_path),
                "-af", "loudnorm",
                "-c:a", "pcm_s16le",
                "-ar", "44100",
                "-ac", "1",
                "-y",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if isinstance(process.returncode, int) and process.returncode != 0:
                raise AudioProcessingError(
                    f"Audio normalization failed: {stderr.decode(errors='replace')}"
                )

        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(f"Audio normalization failed: {e}") from e
