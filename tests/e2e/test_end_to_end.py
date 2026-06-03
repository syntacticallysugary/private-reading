"""End-to-end integration tests for Private Reading."""

import asyncio
import json
import tempfile
import pytest
from pathlib import Path

import sys
import os

# Insert the project root (3 levels up from tests/e2e/) so `core` is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from private_reading import app as private_reading_app
from private_reading.config import AppConfig, TTSConfig, ProcessingConfig, LoggingConfig


@pytest.fixture
def tmp_dir(tmp_path):
    """Create a temporary directory for test artifacts."""
    return tmp_path


@pytest.fixture
def app_config(tmp_path):
    """Create a test AppConfig instance."""
    return AppConfig(
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        processed_dir=tmp_path / "processed",
        tts=TTSConfig(endpoint="http://localhost:8008/v1/audio/speech"),
        processing=ProcessingConfig(chunk_size=500),
        logging=LoggingConfig(level="INFO"),
    )


@pytest.fixture
def sample_markdown_file(tmp_path):
    """Create a sample markdown file for testing."""
    markdown_content = """# Test Document

This is a sample document for testing the Private Reading pipeline.

## Introduction

This paragraph introduces the document.

## Conclusion

This concludes the test document.
"""
    file_path = tmp_path / "test_document.md"
    file_path.write_text(markdown_content)
    return file_path


@pytest.fixture
def sample_txt_file(tmp_path):
    """Create a sample text file for testing."""
    txt_content = """Simple text file content.

Multiple paragraphs can be included.

This paragraph has special characters.
"""
    file_path = tmp_path / "test_document.txt"
    file_path.write_text(txt_content)
    return file_path


@pytest.fixture
def integrator(app_config):
    """Create a PrivateReadingApp instance for integration tests."""
    return private_reading_app.PrivateReadingApp(app_config)


async def test_full_pipeline_markdown(integrator, sample_markdown_file):
    """Test the complete pipeline with a markdown file."""
    result = await integrator.process_single_file(sample_markdown_file)

    assert result is not None
    assert result.success is True
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.duration > 0


async def test_full_pipeline_txt_file(integrator, sample_txt_file):
    """Test the complete pipeline with a TXT file."""
    result = await integrator.process_single_file(sample_txt_file)

    assert result is not None
    assert result.success is True
    assert result.output_path is not None
    assert result.output_path.exists()


async def test_output_format(integrator, sample_markdown_file):
    """Test that ProcessingResult has all expected fields."""
    result = await integrator.process_single_file(sample_markdown_file)

    assert hasattr(result, "success")
    assert hasattr(result, "output_path")
    assert hasattr(result, "error")
    assert hasattr(result, "duration")


async def test_pipeline_error_handling(tmp_path, integrator):
    """Test that pipeline handles errors gracefully."""
    empty_file = tmp_path / "empty_file.txt"
    empty_file.write_text("")

    result = await integrator.process_single_file(empty_file)
    assert result is not None


async def test_long_document_chunking(app_config, tmp_path):
    """Test that long documents are properly chunked and processed."""
    content = "# Long Document\n\n"
    for i in range(20):
        content += f"This is paragraph {i} with some content for testing chunking.\n\n"

    long_file = tmp_path / "long_document.md"
    long_file.write_text(content)

    app = private_reading_app.PrivateReadingApp(app_config)
    result = await app.process_single_file(long_file)

    assert result is not None
    assert result.success is True


async def test_sidecar_metadata_written(integrator, sample_txt_file):
    """Test that a sidecar JSON metadata file is written alongside the WAV."""
    result = await integrator.process_single_file(sample_txt_file)

    assert result.success is True
    sidecar = result.output_path.with_stem(f"{result.output_path.stem}.json")
    assert sidecar.exists()

    with open(sidecar, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    assert "source_file" in metadata
    assert "duration" in metadata
