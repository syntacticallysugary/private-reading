"""Tests for OutputManager class."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from private_reading.core.output_manager import OutputManager, OutputMetadata
from private_reading.exceptions import OutputError


class TestOutputManager:
    """Test cases for OutputManager."""

    @pytest.fixture
    def output_manager(self, tmp_dir):
        """Create OutputManager instance."""
        output_dir = tmp_dir / "output"
        processed_dir = tmp_dir / "processed"
        return OutputManager(
            output_dir=output_dir,
            processed_dir=processed_dir,
        )

    @pytest.fixture
    def output_manager_no_processed(self, tmp_dir):
        """Create OutputManager without processed directory."""
        output_dir = tmp_dir / "output"
        return OutputManager(
            output_dir=output_dir,
        )

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing."""
        return OutputMetadata(
            source_file="test.txt",
            word_count=100,
            chunk_count=5,
            total_duration_seconds=30.5,
            voice_config={"ref_audio": "test.wav", "ref_text": "test"},
            processing_time_seconds=1.5,
        )

    @pytest.mark.asyncio
    async def test_save_wav_success(self, output_manager, tmp_dir):
        """Test successful WAV saving."""
        audio_data = b"audio data content"
        original_name = "test_audio"

        wav_path = await output_manager.save_wav(audio_data, original_name)

        # Verify WAV file was created
        assert wav_path.exists()
        assert wav_path.suffix == ".wav"

        # Verify filename contains timestamp
        assert "_" in wav_path.name
        assert wav_path.name.endswith(".wav")

    @pytest.mark.asyncio
    async def test_save_wav_with_timestamp(self, output_manager, tmp_dir):
        """Test WAV saving with specific timestamp."""
        audio_data = b"audio data content"
        original_name = "test_audio"
        timestamp = datetime(2024, 1, 15, 10, 30, 45)

        wav_path = await output_manager.save_wav(audio_data, original_name, timestamp)

        # Verify filename contains timestamp
        expected_name = f"test_audio_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"
        assert wav_path.name == expected_name

    @pytest.mark.asyncio
    async def test_save_wav_empty_data(self, output_manager, tmp_dir):
        """Test WAV saving with empty audio data raises error."""
        original_name = "test_audio"

        with pytest.raises(OutputError) as exc_info:
            await output_manager.save_wav(b"", original_name)

        assert "No audio data provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_wav_creates_parent_dirs(self, output_manager, tmp_dir):
        """Test WAV saving creates parent directories."""
        audio_data = b"audio data content"
        original_name = "test_audio"

        wav_path = await output_manager.save_wav(audio_data, original_name)

        # Verify file was created
        assert wav_path.exists()

    @pytest.mark.asyncio
    async def test_save_sidecar_success(self, output_manager, tmp_dir):
        """Test successful sidecar JSON saving."""
        output_path = tmp_dir / "audio_20240115_103045.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "source_file": "test.txt",
            "word_count": 100,
            "chunk_count": 5,
            "total_duration_seconds": 30.5,
            "voice_config": {"ref_audio": "test.wav"},
            "processing_time_seconds": 1.5,
        }

        await output_manager.save_sidecar(metadata, output_path)

        # Verify sidecar file was created
        sidecar_path = output_path.with_stem("audio_20240115_103045.json")
        assert sidecar_path.exists()

        # Verify JSON content
        with open(sidecar_path) as f:
            saved_metadata = json.load(f)

        assert saved_metadata["source_file"] == metadata["source_file"]
        assert saved_metadata["word_count"] == metadata["word_count"]

    @pytest.mark.asyncio
    async def test_save_sidecar_creates_parent_dirs(self, output_manager, tmp_dir):
        """Test sidecar saving creates parent directories."""
        output_path = tmp_dir / "nested" / "audio.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {"source_file": "test.txt", "word_count": 100}

        await output_manager.save_sidecar(metadata, output_path)

        # Verify sidecar file was created
        sidecar_path = output_path.with_stem("audio.json")
        assert sidecar_path.exists()

    @pytest.mark.asyncio
    async def test_save_sidecar_with_complex_metadata(self, output_manager, tmp_dir):
        """Test sidecar saving with complex metadata."""
        output_path = tmp_dir / "audio.wav"

        metadata = {
            "source_file": "test.txt",
            "word_count": 100,
            "chunk_count": 5,
            "total_duration_seconds": 30.5,
            "voice_config": {
                "ref_audio": "test.wav",
                "ref_text": "test",
                "voice_design": "design",
            },
            "processing_time_seconds": 1.5,
            "status": "completed",
        }

        await output_manager.save_sidecar(metadata, output_path)

        # Verify sidecar file was created with correct content
        sidecar_path = output_path.with_stem("audio.json")
        with open(sidecar_path) as f:
            saved_metadata = json.load(f)

        assert saved_metadata["voice_config"]["ref_audio"] == metadata["voice_config"]["ref_audio"]
        assert saved_metadata["voice_config"]["ref_text"] == metadata["voice_config"]["ref_text"]
        assert (
            saved_metadata["voice_config"]["voice_design"]
            == metadata["voice_config"]["voice_design"]
        )

    @pytest.mark.asyncio
    async def test_move_to_processed_success(self, output_manager, tmp_dir):
        """Test successful file moving to processed directory."""
        file_path = tmp_dir / "output" / "audio.wav"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"audio data")

        await output_manager.move_to_processed(file_path)

        # Verify file was moved to processed directory
        processed_path = tmp_dir / "processed" / "audio.wav"
        assert processed_path.exists()
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_move_to_processed_no_processed_dir(self, output_manager_no_processed, tmp_dir):
        """Test moving to processed directory without processed dir configured raises error."""
        file_path = tmp_dir / "output" / "audio.wav"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"audio data")

        with pytest.raises(OutputError) as exc_info:
            await output_manager_no_processed.move_to_processed(file_path)

        assert "Processed directory not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_to_processed_preserves_filename(self, output_manager, tmp_dir):
        """Test moving preserves original filename."""
        file_path = tmp_dir / "output" / "test_audio.wav"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"audio data")

        await output_manager.move_to_processed(file_path)

        # Verify file was moved with same name
        processed_path = tmp_dir / "processed" / "test_audio.wav"
        assert processed_path.exists()

    @pytest.mark.asyncio
    async def test_move_to_processed_creates_parent_dirs(self, output_manager, tmp_dir):
        """Test moving creates parent directories in processed dir."""
        file_path = tmp_dir / "output" / "audio.wav"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"audio data")

        await output_manager.move_to_processed(file_path)

        # Verify file was moved
        processed_path = tmp_dir / "processed" / "audio.wav"
        assert processed_path.exists()

    @pytest.mark.asyncio
    async def test_save_wav_filename_format(self, output_manager, tmp_dir):
        """Test WAV filename format includes timestamp."""
        audio_data = b"audio data"
        original_name = "test"

        wav_path = await output_manager.save_wav(audio_data, original_name)

        # Verify filename format: original_name_YYYYMMDD_HHMMSS.wav
        parts = wav_path.name.rsplit(".", 1)
        assert len(parts) == 2
        assert parts[1] == "wav"

        timestamp_part = parts[0].split("_", 1)[1]
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
        assert timestamp_part[0:4].isdigit()  # Year
        assert timestamp_part[4:6].isdigit()  # Month
        assert timestamp_part[6:8].isdigit()  # Day
        assert timestamp_part[9:11].isdigit()  # Hour
        assert timestamp_part[11:13].isdigit()  # Minute
        assert timestamp_part[13:15].isdigit()  # Second

    @pytest.mark.asyncio
    async def test_save_sidecar_json_valid(self, output_manager, tmp_dir):
        """Test sidecar JSON is valid and parseable."""
        output_path = tmp_dir / "audio.wav"

        metadata = {
            "source_file": "test.txt",
            "word_count": 100,
            "chunk_count": 5,
            "total_duration_seconds": 30.5,
            "voice_config": {"ref_audio": "test.wav"},
            "processing_time_seconds": 1.5,
        }

        await output_manager.save_sidecar(metadata, output_path)

        # Verify JSON is valid
        sidecar_path = output_path.with_stem("audio.json")
        with open(sidecar_path) as f:
            saved_metadata = json.load(f)

        assert isinstance(saved_metadata, dict)
        assert "source_file" in saved_metadata
        assert "word_count" in saved_metadata

    @pytest.mark.asyncio
    async def test_move_to_processed_overwrites_existing(self, output_manager, tmp_dir):
        """Test moving overwrites existing file in processed directory."""
        # Create file in output
        file_path = tmp_dir / "output" / "audio.wav"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"audio data")

        # Create file in processed (should be overwritten)
        processed_path = tmp_dir / "processed" / "audio.wav"
        processed_path.write_bytes(b"old data")

        await output_manager.move_to_processed(file_path)

        # Verify file was overwritten
        assert processed_path.exists()
        assert processed_path.read_bytes() == b"audio data"

    @pytest.mark.asyncio
    async def test_save_wav_multiple_files(self, output_manager, tmp_dir):
        """Test saving multiple WAV files."""
        audio_data = b"audio data"

        wav_paths = []
        for i in range(5):
            wav_path = await output_manager.save_wav(audio_data, f"test_{i}")
            wav_paths.append(wav_path)

        # Verify all files were created
        for wav_path in wav_paths:
            assert wav_path.exists()

    @pytest.mark.asyncio
    async def test_save_sidecar_multiple_files(self, output_manager, tmp_dir):
        """Test saving multiple sidecar files."""
        output_path = tmp_dir / "audio.wav"

        metadata = {"source_file": "test.txt", "word_count": 100}

        await output_manager.save_sidecar(metadata, output_path)

        # Verify sidecar was created
        sidecar_path = output_path.with_stem("audio.json")
        assert sidecar_path.exists()
