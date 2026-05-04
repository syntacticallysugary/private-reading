"""Concurrency sweep test for myAudible TTS endpoint.

This script tests concurrent TTS requests against the endpoint used
by the rest of the codebase to determine optimal concurrency levels.
"""

import asyncio
import os
import time
import statistics
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from myaudible.core.chunk_manager import ChunkManager, MAX_CHUNK
from myaudible.core.text_extractor import TextExtractor
from myaudible.core.tts_client import TTSClient


async def run_sweep(chunks, concurrency, tts_client):
    """Run TTS sweep test with specified concurrency level.

    Args:
        chunks: List of text chunks to send to TTS endpoint.
        concurrency: Maximum number of concurrent requests.
        tts_client: TTSClient instance to use for requests.

    Returns:
        Dictionary with latency statistics and concurrency level.
    """
    sem = asyncio.Semaphore(concurrency)
    active = 0
    peak_active = 0

    async def timed_generate(chunk):
        """Measure time taken for a single TTS request."""
        nonlocal active, peak_active
        start = time.perf_counter()
        async with sem:
            active += 1
            peak_active = max(peak_active, active)
            await tts_client.generate_speech(chunk)
            active -= 1
        end = time.perf_counter()
        return end - start

    start_total = time.perf_counter()
    latencies = await asyncio.gather(*(timed_generate(c) for c in chunks))
    end_total = time.perf_counter()

    return {
        "concurrency": concurrency,
        "peak_active": peak_active,
        "avg_latency": sum(latencies) / len(latencies),
        "p95_latency": statistics.quantiles(latencies, n=20)[18],
        "total_time": end_total - start_total,
    }


async def sweep(chunks, tts_client):
    """Run sweep across all concurrency levels.

    Args:
        chunks: List of text chunks to send to TTS endpoint.
        tts_client: TTSClient instance to use for requests.

    Returns:
        List of results for each concurrency level tested.
    """
    results = []
    for c in [1, 2, 4, 6, 8, 10, 12, 14]:
        print(f"Testing concurrency={c}")
        r = await run_sweep(chunks, c, tts_client)
        results.append(r)
        print(r)
    return results


async def load_chunks_from_file(file_path: str) -> list:
    """Load text from file and chunk it using the same logic as the main app.

    Args:
        file_path: Path to text file to chunk (can be relative or absolute).

    Returns:
        List of text chunks.
    """
    path = Path(file_path)
    # If relative path doesn't exist, try making it absolute from current directory
    if not path.is_absolute():
        path = Path.cwd() / file_path
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    text = await TextExtractor().extract(path)

    chunk_manager = ChunkManager(max_chars=MAX_CHUNK, overlap_ratio=0.1)
    chunks = await chunk_manager.chunk(text)

    return chunks


async def main():
    """Run the sweep test."""
    # Get environment variables for TTS endpoint
    tts_endpoint = os.getenv("TTS_ENDPOINT", "http://192.168.1.104:8008/v1/audio/speech")
    tts_voice_design = os.getenv("TTS_VOICE_DESIGN", "")

    print(f"TTS Endpoint: {tts_endpoint}")
    print(f"Voice Design: {tts_voice_design}")

    # Load chunks from file - use absolute path
    # Check environment variable first, then try common input files
    file_path = os.getenv("SWEEP_CHUNK_FILE")
    if not file_path:
        # Default: use first available file in input/ directory or subdirectories
        input_dir = Path.cwd() / "input"
        if input_dir.exists():
            # Recursively find all files in input/ directory
            files = list(input_dir.rglob("*"))
            files = [f for f in files if f.is_file()]
            if files:
                # Sort and pick the first file
                files.sort()
                file_path = str(files[0])
            else:
                raise FileNotFoundError("No files found in input/ directory. Set SWEEP_CHUNK_FILE env var or add files to input/")
        else:
            raise FileNotFoundError("input/ directory not found. Set SWEEP_CHUNK_FILE env var to full path of a file to process.")
    
    print(f"Loading chunks from: {file_path}")
    chunks = await load_chunks_from_file(file_path)
    text = await TextExtractor().extract(Path(file_path))
    print(f"Loaded {len(chunks)} chunks ({len(text)} words)")

    # Run sweep with TTS client context
    async with TTSClient(
        endpoint=tts_endpoint,
        voice=tts_voice_design,
        retry_attempts=3,
    ) as tts_client:
        results = await sweep(chunks, tts_client)

    # Print summary
    print("\n=== SUMMARY ===")
    for r in results:
        print(f"Concurrency {r['concurrency']:2d} | Peak: {r['peak_active']:2d} | "
              f"Total: {r['total_time']:8.2f}s | Avg: {r['avg_latency']:7.2f}s | P95: {r['p95_latency']:7.2f}s")

    # Find best concurrency (lowest total time)
    best = min(results, key=lambda x: x["total_time"])
    print(f"\nBest concurrency: {best['concurrency']} (total time: {best['total_time']:.2f}s)")


if __name__ == "__main__":
    asyncio.run(main())
