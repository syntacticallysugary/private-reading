"""Performance tests for Private Reading."""

import time
import pytest
from pathlib import Path

import sys

# Insert the project root (3 levels up from tests/performance/) so `core` is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from private_reading import app as private_reading_app
from private_reading.config import AppConfig, TTSConfig, ProcessingConfig, LoggingConfig


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
def benchmark_app(app_config):
    """Create a PrivateReadingApp instance for benchmarking."""
    return private_reading_app.PrivateReadingApp(app_config)


@pytest.mark.benchmark
async def test_markdown_processing_time(benchmark_app, tmp_path):
    """Benchmark markdown file processing time."""
    document = "# Performance Test\n\n" + "Paragraph content for benchmarking. " * 20 + "\n\n"
    file_path = tmp_path / "benchmark.md"
    file_path.write_text(document)

    start_time = time.time()
    result = await benchmark_app.process_single_file(file_path)
    elapsed_time = time.time() - start_time

    assert result is not None
    assert result.success is True
    print(f"\nMarkdown Processing: {elapsed_time:.3f}s")


@pytest.mark.benchmark
async def test_txt_processing_time(benchmark_app, tmp_path):
    """Benchmark TXT file processing time."""
    document = "Performance test paragraph.\n\n" * 10
    file_path = tmp_path / "benchmark.txt"
    file_path.write_text(document)

    start_time = time.time()
    result = await benchmark_app.process_single_file(file_path)
    elapsed_time = time.time() - start_time

    assert result is not None
    assert result.success is True
    print(f"\nTXT Processing: {elapsed_time:.3f}s")


async def test_multiple_file_processing(app_config, tmp_path):
    """Benchmark processing multiple files in sequence."""
    app = private_reading_app.PrivateReadingApp(app_config)

    for i in range(3):
        (tmp_path / f"doc{i}.md").write_text(
            f"# Document {i}\n\n" + f"Content for document {i}. " * 10 + "\n\n"
        )

    start_time = time.time()
    results = []
    for i in range(3):
        result = await app.process_single_file(tmp_path / f"doc{i}.md")
        results.append(result)
    total_time = time.time() - start_time

    assert len(results) == 3
    assert all(r.success for r in results)
    print(f"\nMultiple Files (3): {total_time:.3f}s total")


async def test_chunk_manager_performance():
    """Benchmark chunk manager with different document sizes."""
    from private_reading.core.chunk_manager import ChunkManager

    manager = ChunkManager(max_chars=500)

    for label, multiplier in [("small", 5), ("medium", 30), ("large", 100)]:
        text = "Benchmark paragraph content for testing. " * multiplier
        start_time = time.time()
        chunks = await manager.chunk(text)
        elapsed_time = time.time() - start_time
        print(f"\n{label.title()}: {elapsed_time:.3f}s, {len(chunks)} chunks")
        assert isinstance(chunks, list)
