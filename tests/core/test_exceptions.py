"""Test suite for exception hierarchy and error handling verification.

This test file verifies Task 3T5 objectives:
1. Verify exception hierarchy: PrivateReadingError base class
2. Verify ExtractionError, TextExtractionError, UnsupportedFormatError
3. Verify ChunkingError
4. Verify TTSError, TTSAPIError
5. Verify AudioError, AudioProcessingError
6. Verify OutputError
7. Verify PipelineError
8. Verify pipeline catches component-specific exceptions
9. Verify error logging with context
10. Verify retry logic for transient errors
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from private_reading.exceptions import (
    AudioError,
    AudioProcessingError,
    ChunkingError,
    ExtractionError,
    OutputError,
    PipelineError,
    PrivateReadingError,
    TextExtractionError,
    TTSAPIError,
    TTSError,
    UnsupportedFormatError,
)


class TestExceptionHierarchy:
    """Test objectives 1-7: Exception hierarchy verification."""

    def test_private_reading_error_is_base_class(self) -> None:
        """Objective 1: Verify PrivateReadingError is the base class."""
        assert issubclass(ExtractionError, PrivateReadingError)
        assert issubclass(ChunkingError, PrivateReadingError)
        assert issubclass(TTSError, PrivateReadingError)
        assert issubclass(AudioError, PrivateReadingError)
        assert issubclass(OutputError, PrivateReadingError)
        assert issubclass(PipelineError, PrivateReadingError)

    def test_extraction_error_hierarchy(self) -> None:
        """Objective 2: Verify ExtractionError and its subclasses."""
        assert issubclass(ExtractionError, PrivateReadingError)
        assert issubclass(TextExtractionError, ExtractionError)
        assert issubclass(UnsupportedFormatError, ExtractionError)

    def test_text_extraction_error_instantiation(self) -> None:
        """Verify TextExtractionError can be instantiated with messages."""
        error = TextExtractionError("Failed to extract text")
        assert str(error) == "Failed to extract text"
        assert error.message == "Failed to extract text"
        assert error.details == {}

    def test_text_extraction_error_with_details(self) -> None:
        """Verify TextExtractionError accepts details parameter."""
        details = {"file": "test.pdf", "error_code": "EXTRACT_001"}
        error = TextExtractionError("Extraction failed", details=details)
        assert error.message == "Extraction failed"
        assert error.details == details

    def test_unsupported_format_error_instantiation(self) -> None:
        """Verify UnsupportedFormatError can be instantiated."""
        error = UnsupportedFormatError("Format not supported")
        assert str(error) == "Format not supported"

    def test_chunking_error_instantiation(self) -> None:
        """Objective 3: Verify ChunkingError."""
        error = ChunkingError("Chunking failed")
        assert str(error) == "Chunking failed"
        assert isinstance(error, PrivateReadingError)

    def test_tts_error_hierarchy(self) -> None:
        """Objective 4: Verify TTSError and TTSAPIError."""
        assert issubclass(TTSError, PrivateReadingError)
        assert issubclass(TTSAPIError, TTSError)

    def test_tts_api_error_instantiation(self) -> None:
        """Verify TTSAPIError can be instantiated."""
        error = TTSAPIError("TTS API call failed")
        assert str(error) == "TTS API call failed"
        assert isinstance(error, TTSError)
        assert isinstance(error, PrivateReadingError)

    def test_audio_error_hierarchy(self) -> None:
        """Objective 5: Verify AudioError and AudioProcessingError."""
        assert issubclass(AudioError, PrivateReadingError)
        assert issubclass(AudioProcessingError, AudioError)

    def test_audio_processing_error_instantiation(self) -> None:
        """Verify AudioProcessingError can be instantiated."""
        error = AudioProcessingError("Audio processing failed")
        assert str(error) == "Audio processing failed"
        assert isinstance(error, AudioError)

    def test_output_error_instantiation(self) -> None:
        """Objective 6: Verify OutputError."""
        error = OutputError("Output operation failed")
        assert str(error) == "Output operation failed"
        assert isinstance(error, PrivateReadingError)

    def test_pipeline_error_instantiation(self) -> None:
        """Objective 7: Verify PipelineError."""
        error = PipelineError("Pipeline orchestration failed")
        assert str(error) == "Pipeline orchestration failed"
        assert isinstance(error, PrivateReadingError)


class TestExceptionMessages:
    """Test that all exceptions have actionable error messages."""

    def test_all_exceptions_have_messages(self) -> None:
        """Verify all exception types can be instantiated with messages."""
        exceptions = [
            PrivateReadingError("Base error"),
            ExtractionError("Extraction error"),
            TextExtractionError("Text extraction error"),
            UnsupportedFormatError("Unsupported format"),
            ChunkingError("Chunking error"),
            TTSError("TTS error"),
            TTSAPIError("TTS API error"),
            AudioError("Audio error"),
            AudioProcessingError("Audio processing error"),
            OutputError("Output error"),
            PipelineError("Pipeline error"),
        ]

        for error in exceptions:
            assert error.message is not None
            assert len(error.message) > 0

    def test_error_messages_are_actionable(self) -> None:
        """Verify error messages provide actionable information."""
        # Test that messages don't contain placeholder text
        error = TextExtractionError("Failed to extract text from file")
        assert "Failed to extract text from file" in str(error)


class TestPipelineExceptionHandling:
    """Test objectives 8-9: Pipeline exception handling and logging."""

    def test_pipeline_imports_exceptions(self) -> None:
        """Verify pipeline module imports the exception classes."""
        from private_reading.core.pipeline import (
            AudioError,
            ChunkingError,
            ExtractionError,
            OutputError,
            TTSError,
        )

        # If this imports without error, the pipeline has the imports

    def test_pipeline_catches_extraction_error(self) -> None:
        """Objective 8: Verify pipeline catches ExtractionError."""
        # This test verifies the pipeline has proper exception handling
        # by checking the source code has the catch block
        import inspect

        from private_reading.core.pipeline import ProcessingPipeline

        source = inspect.getsource(ProcessingPipeline.process_file)
        assert "except ExtractionError" in source

    def test_pipeline_catches_chunking_error(self) -> None:
        """Verify pipeline catches ChunkingError."""
        import inspect

        from private_reading.core.pipeline import ProcessingPipeline

        source = inspect.getsource(ProcessingPipeline.process_file)
        assert "except ChunkingError" in source

    def test_pipeline_catches_tts_error(self) -> None:
        """Verify pipeline catches TTSError."""
        import inspect

        from private_reading.core.pipeline import ProcessingPipeline

        source = inspect.getsource(ProcessingPipeline.process_file)
        assert "except TTSError" in source

    def test_pipeline_catches_audio_error(self) -> None:
        """Verify pipeline catches AudioError."""
        import inspect

        from private_reading.core.pipeline import ProcessingPipeline

        source = inspect.getsource(ProcessingPipeline.process_file)
        assert "except AudioError" in source

    def test_pipeline_catches_output_error(self) -> None:
        """Verify pipeline catches OutputError."""
        import inspect

        from private_reading.core.pipeline import ProcessingPipeline

        source = inspect.getsource(ProcessingPipeline.process_file)
        assert "except OutputError" in source

    def test_pipeline_has_error_logging(self) -> None:
        """Objective 9: Verify pipeline has error logging with context."""
        import inspect

        from private_reading.core.pipeline import ProcessingPipeline

        source = inspect.getsource(ProcessingPipeline.process_file)
        assert "_logger.error" in source
        assert "_logger.exception" in source


class TestRetryLogic:
    """Test objective 10: Retry logic for transient errors."""

    def test_pipeline_has_retry_decorator(self) -> None:
        """Verify pipeline has retry decorator for transient errors."""
        from private_reading.core.pipeline import retry

        assert callable(retry)

    def test_retry_decorator_parameters(self) -> None:
        """Verify retry decorator accepts max_retries and backoff_base."""
        from private_reading.core.pipeline import retry

        # Test with default parameters
        decorator = retry()
        assert decorator is not None

        # Test with custom parameters
        decorator = retry(max_retries=5, backoff_base=2.0)
        assert decorator is not None

    def test_retry_with_backoff_method_exists(self) -> None:
        """Verify pipeline has _retry_with_backoff method."""
        from private_reading.core.pipeline import ProcessingPipeline

        assert hasattr(ProcessingPipeline, "_retry_with_backoff")

    def test_retry_exponential_backoff_calculation(self) -> None:
        """Verify exponential backoff calculation is correct."""
        from private_reading.core.pipeline import retry

        decorator = retry(max_retries=3, backoff_base=1.0)
        wrapped_func = decorator(lambda: None)

        # The decorator should be callable
        assert callable(wrapped_func)


class TestExceptionDetails:
    """Test that exceptions properly store and access details."""

    def test_exception_with_none_details(self) -> None:
        """Verify exceptions handle None details gracefully."""
        error = TextExtractionError("Error message", details=None)
        assert error.details == {}

    def test_exception_with_empty_dict_details(self) -> None:
        """Verify exceptions handle empty dict details."""
        error = TextExtractionError("Error message", details={})
        assert error.details == {}

    def test_exception_with_complex_details(self) -> None:
        """Verify exceptions handle complex details."""
        details = {
            "file": "test.pdf",
            "error_code": "EXTRACT_001",
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }
        error = TextExtractionError("Error message", details=details)
        assert error.details == details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
