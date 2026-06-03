"""CLI interface tests for Private Reading (Task 3T4)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from private_reading.cli import create_argument_parser, validate_inputs, build_config
from private_reading.core.chunk_manager import MAX_CHUNK


# ---------------------------------------------------------------------------
# Argument parser structure
# ---------------------------------------------------------------------------

class TestArgumentParser:

    @pytest.fixture
    def parser(self):
        return create_argument_parser()

    def test_help_contains_required_args(self, parser):
        help_text = parser.format_help()
        for flag in ["-i", "--input", "-o", "--output"]:
            assert flag in help_text, f"Missing {flag} from --help"

    def test_help_contains_optional_args(self, parser):
        help_text = parser.format_help()
        for flag in ["-c", "--config", "--voice", "--chunk-size", "--overlap-ratio",
                     "-v", "--verbose", "-w", "--watch"]:
            assert flag in help_text, f"Missing {flag} from --help"

    def test_missing_all_args_exits_2(self, parser):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args([])
        assert exc.value.code == 2

    def test_missing_output_exits_2(self, parser):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["-i", "/tmp/file.txt"])
        assert exc.value.code == 2

    def test_missing_input_exits_2(self, parser):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["-o", "/tmp/out"])
        assert exc.value.code == 2

    def test_watch_flag_parsed(self, parser):
        args = parser.parse_args(["-i", "/tmp", "-o", "/tmp/out", "-w"])
        assert args.watch is True

    def test_verbose_flag_parsed(self, parser):
        args = parser.parse_args(["-i", "/tmp", "-o", "/tmp/out", "-v"])
        assert args.verbose is True

    def test_chunk_size_parsed(self, parser):
        args = parser.parse_args(["-i", "/tmp", "-o", "/tmp/out", "--chunk-size", "1000"])
        assert args.chunk_size == 1000

    def test_overlap_ratio_parsed(self, parser):
        args = parser.parse_args(["-i", "/tmp", "-o", "/tmp/out", "--overlap-ratio", "0.2"])
        assert abs(args.overlap_ratio - 0.2) < 1e-9

    def test_voice_parsed(self, parser):
        args = parser.parse_args(["-i", "/tmp", "-o", "/tmp/out", "--voice", "echo"])
        assert args.voice == "echo"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestValidateInputs:

    def _make_args(self, tmp_path, input_path=None, output_path=None,
                   chunk_size=None, overlap_ratio=None, verbose=False, watch=False):
        return argparse.Namespace(
            input=str(input_path or tmp_path),
            output=str(output_path or (tmp_path / "out")),
            chunk_size=chunk_size,
            overlap_ratio=overlap_ratio,
            verbose=verbose,
            watch=watch,
            config=None,
            voice=None,
        )

    def test_nonexistent_input_returns_false(self, tmp_path, capsys):
        args = self._make_args(tmp_path, input_path=Path("/nonexistent/path.txt"))
        assert validate_inputs(args) is False
        assert "does not exist" in capsys.readouterr().err

    def test_valid_directory_input_returns_true(self, tmp_path):
        (tmp_path / "out").mkdir()
        args = self._make_args(tmp_path, input_path=tmp_path, output_path=tmp_path / "out")
        assert validate_inputs(args) is True

    def test_valid_file_input_returns_true(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hello")
        (tmp_path / "out").mkdir()
        args = self._make_args(tmp_path, input_path=f, output_path=tmp_path / "out")
        assert validate_inputs(args) is True

    def test_nonpositive_chunk_size_returns_false(self, tmp_path, capsys):
        args = self._make_args(tmp_path, chunk_size=0)
        assert validate_inputs(args) is False
        assert "chunk size" in capsys.readouterr().err.lower()

    def test_overlap_ratio_out_of_range_returns_false(self, tmp_path, capsys):
        args = self._make_args(tmp_path, overlap_ratio=1.5)
        assert validate_inputs(args) is False
        assert "overlap ratio" in capsys.readouterr().err.lower()

    def test_output_dir_created_if_missing(self, tmp_path):
        new_dir = tmp_path / "brand_new_dir"
        assert not new_dir.exists()
        args = self._make_args(tmp_path, output_path=new_dir)
        validate_inputs(args)
        assert new_dir.exists()


# ---------------------------------------------------------------------------
# Config building
# ---------------------------------------------------------------------------

class TestBuildConfig:

    def _make_args(self, tmp_path, **kwargs):
        defaults = dict(
            input=str(tmp_path),
            output=str(tmp_path / "out"),
            chunk_size=None,
            overlap_ratio=None,
            verbose=False,
            watch=False,
            config=None,
            voice=None,
        )
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_chunk_size_override_applied(self, tmp_path):
        args = self._make_args(tmp_path, chunk_size=1000)
        config = build_config(args)
        assert config.processing.chunk_size == 1000

    def test_overlap_ratio_override_applied(self, tmp_path):
        args = self._make_args(tmp_path, overlap_ratio=0.25)
        config = build_config(args)
        assert abs(config.processing.overlap_ratio - 0.25) < 1e-9

    def test_verbose_sets_debug_level(self, tmp_path):
        args = self._make_args(tmp_path, verbose=True)
        config = build_config(args)
        assert config.logging.level == "DEBUG"

    def test_default_level_is_info(self, tmp_path):
        args = self._make_args(tmp_path, verbose=False)
        config = build_config(args)
        assert config.logging.level == "INFO"

    def test_file_input_sets_single_file_mode(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hello")
        args = self._make_args(tmp_path, input=str(f))
        config = build_config(args)
        assert config.input_dir == f.parent

    def test_processed_dir_set_under_output(self, tmp_path):
        args = self._make_args(tmp_path)
        config = build_config(args)
        assert config.processed_dir == Path(args.output) / "processed"

    def test_default_chunk_size_is_max_chunk(self, tmp_path):
        args = self._make_args(tmp_path, chunk_size=None)
        config = build_config(args)
        assert config.processing.chunk_size == MAX_CHUNK, f"Expected {MAX_CHUNK}, got {config.processing.chunk_size}"


# ---------------------------------------------------------------------------
# End-to-end subprocess tests
# ---------------------------------------------------------------------------

class TestCLISubprocess:

    def run_cli(self, *args, timeout=30):
        return subprocess.run(
            [sys.executable, "-m", "private_reading", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_help_exits_zero(self):
        result = self.run_cli("--help")
        assert result.returncode == 0
        assert "--input" in result.stdout
        assert "--output" in result.stdout
        assert "--watch" in result.stdout

    def test_no_args_exits_2(self):
        result = self.run_cli()
        assert result.returncode == 2

    def test_missing_output_exits_2(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hello")
        result = self.run_cli("-i", str(f))
        assert result.returncode == 2

    def test_nonexistent_input_exits_1(self, tmp_path):
        result = self.run_cli("-i", "/nonexistent/file.txt", "-o", str(tmp_path / "out"))
        assert result.returncode == 1
        assert "does not exist" in result.stderr

    def test_negative_chunk_size_exits_1(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hello")
        result = self.run_cli("-i", str(f), "-o", str(tmp_path / "out"), "--chunk-size", "-5")
        assert result.returncode == 1
        assert "chunk size" in result.stderr.lower()

    def test_processes_txt_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world.\n\nSecond paragraph here.")
        out = tmp_path / "output"
        result = self.run_cli("-i", str(f), "-o", str(out), timeout=60)
        assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
        wav_files = list(out.glob("*.wav"))
        assert len(wav_files) > 0, "No WAV file produced"

    def test_processes_markdown_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nFirst paragraph.\n\nSecond paragraph.")
        out = tmp_path / "output"
        result = self.run_cli("-i", str(f), "-o", str(out), timeout=60)
        assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
        wav_files = list(out.glob("*.wav"))
        assert len(wav_files) > 0

    def test_chunk_size_override_accepted(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Short text.")
        out = tmp_path / "output"
        result = self.run_cli("-i", str(f), "-o", str(out), "--chunk-size", "1000", timeout=60)
        assert result.returncode == 0, f"CLI failed:\n{result.stderr}"

    def test_verbose_flag_accepted(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Short text.")
        out = tmp_path / "output"
        result = self.run_cli("-i", str(f), "-o", str(out), "-v", timeout=60)
        assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
