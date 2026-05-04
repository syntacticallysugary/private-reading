"""Command-line interface for myAudible."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from myaudible.config import AppConfig, TTSConfig, ProcessingConfig, LoggingConfig, SemaphoreConfig
from myaudible.core.chunk_manager import MAX_CHUNK
from myaudible.app import MyAudibleApp


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="myaudible",
        description="myAudible - Convert text documents to audiobooks using TTS",
        epilog=(
            "Examples:\n"
            "  python -m myaudible -i document.md -o ./output\n"
            "  python -m myaudible -i ./documents -o ./output -w\n"
            "  python -m myaudible -i document.md -o ./output -v --voice echo\n"
        ),
    )

    required = parser.add_argument_group("required arguments")
    required.add_argument("-i", "--input", required=True, help="Input file or directory path")
    required.add_argument("-o", "--output", required=True, help="Output directory path")

    optional = parser.add_argument_group("optional arguments")
    optional.add_argument("-c", "--config", default=None, help="Path to configuration file")
    optional.add_argument("--voice", default=None, help="Voice ID for TTS")
    optional.add_argument("--chunk-size", type=int, default=None, help="Override max chunk size in characters")
    optional.add_argument("--overlap-ratio", type=float, default=None, help="Override overlap ratio (0.0-1.0)")
    optional.add_argument("--semaphore-size", type=int, default=None, help="Override semaphore size for concurrency control (1-50)")
    optional.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug logging")
    optional.add_argument("-w", "--watch", action="store_true", help="Enable file watcher mode")

    return parser


def validate_inputs(args: argparse.Namespace) -> bool:
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input path does not exist: {args.input}", file=sys.stderr)
        return False

    if not input_path.is_file() and not input_path.is_dir():
        print(f"Error: Input path is neither a file nor a directory: {args.input}", file=sys.stderr)
        return False

    if output_path.exists():
        if not output_path.is_dir():
            print(f"Error: Output path exists but is not a directory: {args.output}", file=sys.stderr)
            return False
        if not os.access(output_path, os.W_OK):
            print(f"Error: Output directory is not writable: {args.output}", file=sys.stderr)
            return False
    else:
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error: Cannot create output directory: {e}", file=sys.stderr)
            return False

    if args.chunk_size is not None and args.chunk_size <= 0:
        print(f"Error: Chunk size must be positive, got: {args.chunk_size}", file=sys.stderr)
        return False

    if args.overlap_ratio is not None and not (0.0 <= args.overlap_ratio <= 1.0):
        print(f"Error: Overlap ratio must be between 0.0 and 1.0, got: {args.overlap_ratio}", file=sys.stderr)
        return False

    if args.semaphore_size is not None and not (1 <= args.semaphore_size <= 50):
        print(f"Error: Semaphore size must be between 1 and 50, got: {args.semaphore_size}", file=sys.stderr)
        return False

    return True


def build_config(args: argparse.Namespace) -> AppConfig:
    input_path = Path(args.input)
    output_path = Path(args.output)

    return AppConfig(
        input_dir=input_path if input_path.is_dir() else input_path.parent,
        output_dir=output_path,
        processed_dir=output_path / "processed",
        tts=TTSConfig(voice_design=args.voice or ""),
        processing=ProcessingConfig(
            chunk_size=args.chunk_size if args.chunk_size is not None else MAX_CHUNK,
            overlap_ratio=args.overlap_ratio if args.overlap_ratio is not None else 0.1,
        ),
        semaphore=SemaphoreConfig(
            size=args.semaphore_size if args.semaphore_size is not None else 10,
        ),
        logging=LoggingConfig(
            level="DEBUG" if args.verbose else "INFO",
        ),
    )


def main() -> None:
    parser = create_argument_parser()
    args = parser.parse_args()

    if not validate_inputs(args):
        sys.exit(1)

    config = build_config(args)
    app = MyAudibleApp(config)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
