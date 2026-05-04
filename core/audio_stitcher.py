"""Audio stitching for myAudible.

This module provides the AudioStitcher class for combining WAV chunks
into final output using ffmpeg.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional

from myaudible.exceptions import AudioProcessingError


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
            raise AudioProcessingError("No WAV files to stitch", {"count": len(wav_files)})

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build concat list with silence files if needed
        concat_list = output_path.with_suffix(".txt")
        concat_files = list(wav_files)  # work on a copy
        
        if add_silence_between and len(wav_files) > 1:
            for i in range(len(wav_files) - 1):
                silence_file = await self.add_silence(
                    self._generate_silence(silence_duration_ms),
                    silence_duration_ms,
                )
                concat_files.insert(2 * i + 1, silence_file)

        with open(concat_list, "w") as f:
            for wav_file in concat_files:
                f.write(f"file '{wav_file}'\n")

        # Run ffmpeg concat demuxer
        cmd = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-y",
            str(output_path),
        ]

        logging.getLogger(__name__).info("Stitching %d files to %s", len(concat_files), output_path)
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise AudioProcessingError(
                "ffmpeg stitching failed",
                {"stderr": stderr.decode()},
            )

        # Clean up concat list
        concat_list.unlink(missing_ok=True)

    async def add_silence(
        self,
        silence_path: Path,
        duration_ms: int,
    ) -> None:
        """Generate silence asset.

        Args:
            silence_path: Path to save the silence file.
            duration_ms: Duration in milliseconds.
        """
        silence_path.parent.mkdir(parents=True, exist_ok=True)

        duration_sec = duration_ms / 1000

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration_sec),
            silence_path,
        ]

        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise AudioProcessingError(
                "Silence generation failed",
                {"stderr": stderr.decode()},
            )

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
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-af", "loudnorm=I=-16:TP=-2:LRA=11",
            "-y",
            str(output_path),
        ]

        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise AudioProcessingError(
                "Audio normalization failed",
                {"stderr": stderr.decode()},
            )

    def _generate_silence(self, duration_ms: int) -> Path:
        """Generate a temporary silence file.

        Args:
            duration_ms: Duration in milliseconds.

        Returns:
            Path to the generated silence file.
        """
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        return Path(path)
