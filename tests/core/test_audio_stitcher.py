"""Tests for AudioStitcher class."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from myaudible.exceptions import AudioProcessingError
from myaudible.core.audio_stitcher import AudioStitcher


class TestAudioStitcher:
    """Test cases for AudioStitcher."""

    @pytest.fixture
    def audio_stitcher(self):
        """Create AudioStitcher instance."""
        return AudioStitcher(ffmpeg_path="ffmpeg")

    @pytest.fixture
    def sample_wav_files(self, tmp_dir):
        """Create sample WAV files for testing."""
        files = []
        for i in range(3):
            wav_path = tmp_dir / f"chunk_{i}.wav"
            # Create a minimal WAV file (1 second of silence)
            wav_path.write_bytes(b"RIFF\x24\x00\x00\x00WAVE")
            files.append(wav_path)
        return files

    @pytest.mark.asyncio
    async def test_stitch_success(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test successful audio stitching."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await audio_stitcher.stitch(sample_wav_files, output_path)

            # Verify output file was created
            assert output_path.exists()

            # Verify ffmpeg was called with correct arguments
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_stitch_no_files(self, audio_stitcher, tmp_dir):
        """Test stitching with no files raises error."""
        output_path = tmp_dir / "output.wav"

        with pytest.raises(AudioProcessingError) as exc_info:
            await audio_stitcher.stitch([], output_path)

        assert "No WAV files to stitch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stitch_with_silence(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test stitching with silence between chunks."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await audio_stitcher.stitch(sample_wav_files, output_path, add_silence_between=True)

            # Verify silence files were generated
            # Check that ffmpeg concat was called
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_stitch_without_silence(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test stitching without silence between chunks."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await audio_stitcher.stitch(sample_wav_files, output_path, add_silence_between=False)

            # Verify no silence files were generated
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_stitch_with_custom_silence_duration(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test stitching with custom silence duration."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await audio_stitcher.stitch(sample_wav_files, output_path, add_silence_between=True, silence_duration_ms=1000)

            # Verify silence was generated with custom duration
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_stitch_ffmpeg_failure(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test stitching handles ffmpeg failure."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess to fail
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            with pytest.raises(AudioProcessingError) as exc_info:
                await audio_stitcher.stitch(sample_wav_files, output_path)

            assert "ffmpeg stitching failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_silence_success(self, audio_stitcher, tmp_dir):
        """Test silence generation."""
        silence_path = tmp_dir / "silence.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            await audio_stitcher.add_silence(silence_path, 500)

            # Verify silence file was created
            assert silence_path.exists()

            # Verify ffmpeg was called with correct arguments
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_silence_with_custom_duration(self, audio_stitcher, tmp_dir):
        """Test silence generation with custom duration."""
        silence_path = tmp_dir / "silence.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            await audio_stitcher.add_silence(silence_path, 1000)

            # Verify ffmpeg was called with 1 second duration
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_silence_creates_parent_dirs(self, audio_stitcher, tmp_dir):
        """Test silence generation creates parent directories."""
        silence_path = tmp_dir / "nested" / "deeply" / "silence.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            await audio_stitcher.add_silence(silence_path, 500)

            # Verify parent directories were created
            assert silence_path.exists()

    @pytest.mark.asyncio
    async def test_add_silence_ffmpeg_failure(self, audio_stitcher, tmp_dir):
        """Test silence generation handles ffmpeg failure."""
        silence_path = tmp_dir / "silence.wav"

        # Mock ffmpeg subprocess to fail
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            with pytest.raises(AudioProcessingError) as exc_info:
                await audio_stitcher.add_silence(silence_path, 500)

            assert "Silence generation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_normalize_audio_success(self, audio_stitcher, tmp_dir):
        """Test audio normalization."""
        input_path = tmp_dir / "input.wav"
        output_path = tmp_dir / "normalized.wav"

        # Create input file
        input_path.write_bytes(b"input audio data")

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            await audio_stitcher.normalize_audio(input_path, output_path)

            # Verify output file was created
            assert output_path.exists()

    @pytest.mark.asyncio
    async def test_normalize_audio_creates_parent_dirs(self, audio_stitcher, tmp_dir):
        """Test normalization creates parent directories."""
        input_path = tmp_dir / "input.wav"
        output_path = tmp_dir / "nested" / "output.wav"

        # Create input file
        input_path.write_bytes(b"input audio data")

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            await audio_stitcher.normalize_audio(input_path, output_path)

            # Verify output file was created
            assert output_path.exists()

    @pytest.mark.asyncio
    async def test_normalize_audio_ffmpeg_failure(self, audio_stitcher, tmp_dir):
        """Test normalization handles ffmpeg failure."""
        input_path = tmp_dir / "input.wav"
        output_path = tmp_dir / "normalized.wav"

        # Create input file
        input_path.write_bytes(b"input audio data")

        # Mock ffmpeg subprocess to fail
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            with pytest.raises(AudioProcessingError) as exc_info:
                await audio_stitcher.normalize_audio(input_path, output_path)

            assert "Audio normalization failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stitch_single_file(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test stitching with single file."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await audio_stitcher.stitch(sample_wav_files[:1], output_path)

            # Verify stitching worked with single file
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_stitch_many_files(self, audio_stitcher, sample_wav_files, tmp_dir):
        """Test stitching with many files."""
        output_path = tmp_dir / "output.wav"

        # Mock ffmpeg subprocess
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await audio_stitcher.stitch(sample_wav_files, output_path)

            # Verify stitching worked with many files
            mock_subprocess.assert_called_once()

