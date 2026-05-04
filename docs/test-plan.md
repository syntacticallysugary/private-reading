# myAudible - Test Plan

## Document Information

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0.0 | 2026-04-19 | Test Lead | Draft |

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Testing Strategy Overview](#testing-strategy-overview)
3. [Golden Dataset - Constraint Definitions](#golden-dataset---constraint-definitions)
4. [Test Architecture](#test-architecture)
5. [Test Categories](#test-categories)
6. [Risk-Adjusted Testing Strategy](#risk-adjusted-testing-strategy)
7. [Defect Lifecycle Management](#defect-lifecycle-management)
8. [Test Data Management](#test-data-management)
9. [Performance Testing](#performance-testing)
10. [Security Testing](#security-testing)
11. [Test Environment Setup](#test-environment-setup)
12. [Test Execution Plan](#test-execution-plan)
13. [Acceptance Criteria](#acceptance-criteria)
14. [Appendix](#appendix)

---

## 1. Executive Summary

This test plan defines the comprehensive quality assurance strategy for the myAudible project - an AI-powered data pipeline that converts text documents (.md, .pdf, .txt, .docx) into high-quality audio files using the Qwen 3.0 TTS model.

### 1.1 Testing Philosophy

As the Test Lead, I adhere to the following principles:

- **Shift Left**: Define requirements and acceptance criteria before code implementation
- **Shift Right**: Monitor behavior in production-like environments
- **Code as Liability**: Every line of code is a liability until proven otherwise through testing
- **Golden Dataset**: Maintain a set of constraints that define expected behavior
- **Risk-Adjusted**: Focus deep testing on high-risk business logic while maintaining broad smoke coverage for low-risk components

### 1.2 Testing Scope

| In Scope | Out of Scope |
|----------|--------------|
| Text extraction from all supported formats | Web interface testing (not in scope) |
| Semantic chunking with semchunk | User authentication testing |
| TTS API integration with Qwen 3.0 | Cloud storage integration |
| Audio stitching with ffmpeg | Mobile application testing |
| File monitoring via systemd/inotify | Third-party API testing (except Qwen) |
| Error handling and recovery | Performance testing of Qwen API itself |

---

## 2. Testing Strategy Overview

### 2.1 Test Pyramid

```
                    ┌─────────────────────────┐
                    │   E2E Tests (10-15%)    │
                    │   Full pipeline flows   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │ Integration Tests (25%) │
                    │ Component interactions  │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Unit Tests (60-65%)   │
                    │   Individual components │
                    └─────────────────────────┘
```

### 2.2 Test Types by Category

| Test Type | Purpose | Tools | Coverage Target |
|-----------|---------|-------|-----------------|
| Unit Tests | Validate individual components | pytest, unittest | 80%+ line coverage |
| Integration Tests | Validate component interactions | pytest-asyncio | Critical paths |
| E2E Tests | Validate full pipeline | pytest | Key user journeys |
| Negative Tests | Validate error handling | pytest | All error paths |
| Performance Tests | Validate throughput/latency | pytest-benchmark | SLA compliance |
| Security Tests | Validate input validation | pytest | OWASP Top 10 |
| Contract Tests | Validate API contracts | pytest | API compatibility |

---

## 3. Golden Dataset - Constraint Definitions

The Golden Dataset defines the immutable constraints that the system must satisfy. These are the "truth" against which all testing is measured.

### 3.1 Functional Constraints

| Constraint ID | Description | Expected Behavior | Validation Method |
|---------------|-------------|-------------------|-------------------|
| GC-001 | Input format support | System accepts .md, .pdf, .txt, .docx | Unit test |
| GC-002 | Output format | System produces .wav files | Unit test |
| GC-003 | Sidecar metadata | JSON metadata accompanies each output | Unit test |
| GC-004 | Chunk size limit | No chunk exceeds 500 characters | Unit test |
| GC-005 | Chunk overlap | 10% overlap between consecutive chunks | Unit test |
| GC-006 | Silence injection | 500ms silence between paragraph breaks | Integration test |
| GC-007 | Audio normalization | Peak normalization applied | Integration test |
| GC-008 | File naming | Output: {original_name}_{timestamp}.wav | Unit test |

### 3.2 Performance Constraints

| Constraint ID | Description | Expected Behavior | Validation Method |
|---------------|-------------|-------------------|-------------------|
| PC-001 | Throughput | 2 min audio per 1 min processing | Performance test |
| PC-002 | Parallelism | Support MAX_PARALLEL concurrent files | Performance test |
| PC-003 | API response time | TTS API responds under 200ms (healthy) | Performance test |
| PC-004 | Memory usage | No memory leaks during processing | Performance test |
| PC-005 | Startup time | Service starts under 5 seconds | Performance test |

### 3.3 Reliability Constraints

| Constraint ID | Description | Expected Behavior | Validation Method |
|---------------|-------------|-------------------|-------------------|
| RC-001 | Retry behavior | Exponential backoff on 5xx/429 | Integration test |
| RC-002 | Max retries | Maximum 3 retry attempts | Integration test |
| RC-003 | Partial recovery | Resume from checkpoint on restart | Integration test |
| RC-004 | File locking | No concurrent processing of same file | Integration test |
| RC-005 | Atomic operations | Process completes or rolls back fully | Integration test |

### 3.4 Security Constraints

| Constraint ID | Description | Expected Behavior | Validation Method |
|---------------|-------------|-------------------|-------------------|
| SC-001 | Input validation | Reject unsupported file types | Security test |
| SC-002 | Path traversal | Block '..' in file paths | Security test |
| SC-003 | File size limit | Reject files > 10MB | Security test |
| SC-004 | Encoding validation | Handle UTF-8, detect legacy encodings | Security test |
| SC-005 | Control character removal | Strip dangerous control characters | Security test |

### 3.5 Data Quality Constraints

| Constraint ID | Description | Expected Behavior | Validation Method |
|---------------|-------------|-------------------|-------------------|
| DC-001 | Text extraction fidelity | Extract all meaningful text | Integration test |
| DC-002 | Markdown stripping | Remove markdown syntax | Unit test |
| DC-003 | PDF reading order | Preserve logical reading order | Integration test |
| DC-004 | DOCX paragraph flow | Maintain document structure | Integration test |
| DC-005 | Encoding preservation | No character corruption | Integration test |

---

## 4. Test Architecture

### 4.1 Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # pytest configuration
├── requirements-test.txt          # Test-only dependencies
│
├── unit/                          # Unit tests (isolated component testing)
│   ├── __init__.py
│   ├── test_text_extractor.py
│   ├── test_chunk_manager.py
│   ├── test_tts_client.py
│   ├── test_audio_stitcher.py
│   ├── test_output_manager.py
│   ├── test_file_watcher.py
│   └── test_config.py
│
├── integration/                   # Integration tests (component interactions)
│   ├── __init__.py
│   ├── test_processing_pipeline.py
│   ├── test_file_watcher_integration.py
│   ├── test_tts_api_integration.py
│   ├── test_audio_stitcher_integration.py
│   └── test_end_to_end_pipeline.py
│
├── e2e/                           # End-to-end tests (full pipeline)
│   ├── __init__.py
│   ├── test_full_pipeline.py
│   ├── test_systemd_integration.py
│   └── test_performance_benchmark.py
│
├── fixtures/                      # Test data fixtures
│   ├── __init__.py
│   ├── sample.md
│   ├── sample.pdf
│   ├── sample.txt
│   ├── sample.docx
│   ├── sample_large.md            # For performance testing
│   ├── sample_markdown.md         # For markdown stripping tests
│   ├── sample_with_tables.docx    # For DOCX table extraction
│   └── sample_multilingual.txt    # For encoding tests
│
├── mocks/                         # Mock servers and clients
│   ├── __init__.py
│   ├── mock_tts_server.py         # Mock Qwen TTS API
│   ├── mock_file_system.py        # Mock file system operations
│   └── fixtures.py                # Mock fixture generators
│
├── security/                      # Security-specific tests
│   ├── __init__.py
│   ├── test_input_validation.py
│   ├── test_path_traversal.py
│   ├── test_encoding_attacks.py
│   └── test_file_size_limits.py
│
├── performance/                   # Performance-specific tests
│   ├── __init__.py
│   ├── test_throughput.py
│   ├── test_memory_usage.py
│   ├── test_api_latency.py
│   └── test_concurrent_processing.py
│
└── negative/                      # Negative testing
    ├── __init__.py
    ├── test_invalid_inputs.py
    ├── test_api_failures.py
    ├── test_disk_space_errors.py
    └── test_network_failures.py
```

### 4.2 Test Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_text():
    """Provide sample text for testing."""
    return "This is a test document. It contains multiple sentences. " * 10

@pytest.fixture
def mock_config():
    """Provide a mock configuration object."""
    config = Mock()
    config.tts.endpoint = "http://mock-tts:8008/v1/audio/speech"
    config.tts.model = "qwen-3.0-tts"
    config.tts.retry_attempts = 3
    config.processing.input_dir = "/tmp/input"
    config.processing.output_dir = "/tmp/output"
    config.processing.chunk_max_chars = 500
    config.processing.chunk_overlap_ratio = 0.1
    config.processing.max_parallel_jobs = 2
    return config

# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_md_file(temp_dir):
    """Create a sample markdown file."""
    file_path = temp_dir / "sample.md"
    file_path.write_text("# Header\n\n**Bold text** and *italic text*\n\n- List item\n\n```code block```\n\nPlain text content.")
    return file_path

@pytest.fixture
def sample_txt_file(temp_dir):
    """Create a sample text file."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is plain text content for testing.")
    return file_path

@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create a sample PDF file for testing."""
    # Note: In real tests, use a pre-generated PDF fixture
    return temp_dir / "sample.pdf"

@pytest.fixture
def sample_docx_file(temp_dir):
    """Create a sample DOCX file for testing."""
    # Note: In real tests, use a pre-generated DOCX fixture
    return temp_dir / "sample.docx"

# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_aiohttp_session():
    """Provide a mock aiohttp ClientSession."""
    with patch('aiohttp.ClientSession') as mock_session:
        yield mock_session

@pytest.fixture
def mock_tts_response():
    """Provide a mock TTS API response."""
    return {
        "audio": "base64_encoded_audio_data",
        "duration_seconds": 5.2,
        "model": "qwen-3.0-tts"
    }

# ============================================================================
# Component Fixtures
# ============================================================================

@pytest.fixture
def text_extractor(mock_config):
    """Provide a configured TextExtractor instance."""
    from myaudible.core.text_extractor import TextExtractor
    return TextExtractor()

@pytest.fixture
def chunk_manager(mock_config):
    """Provide a configured ChunkManager instance."""
    from myaudible.core.chunk_manager import ChunkManager
    return ChunkManager(
        max_chars=mock_config.processing.chunk_max_chars,
        overlap_ratio=mock_config.processing.chunk_overlap_ratio
    )

@pytest.fixture
def tts_client(mock_config):
    """Provide a configured TTSClient instance."""
    from myaudible.core.tts_client import TTSClient
    return TTSClient(
        endpoint=mock_config.tts.endpoint,
        retry_attempts=mock_config.tts.retry_attempts
    )

@pytest.fixture
def audio_stitcher():
    """Provide an AudioStitcher instance."""
    from myaudible.core.audio_stitcher import AudioStitcher
    return AudioStitcher()

@pytest.fixture
def output_manager(temp_dir, mock_config):
    """Provide a configured OutputManager instance."""
    from myaudible.core.output_manager import OutputManager
    return OutputManager(
        output_dir=temp_dir / "output",
        processed_dir=temp_dir / "processed"
    )
```

---

## 5. Test Categories

### 5.1 Unit Tests

Unit tests validate individual components in isolation. They are fast, deterministic, and provide the foundation of our test suite.

#### 5.1.1 TextExtractor Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-TE-001 | test_extract_markdown | Extract text from markdown file | Plain text without markdown syntax |
| UT-TE-002 | test_extract_markdown_headers | Strip markdown headers | No '#' characters in output |
| UT-TE-003 | test_extract_markdown_bold | Strip bold markdown | No '**' characters in output |
| UT-TE-004 | test_extract_markdown_italic | Strip italic markdown | No '*' characters in output |
| UT-TE-005 | test_extract_markdown_code_blocks | Remove code blocks | No '```' blocks in output |
| UT-TE-006 | test_extract_markdown_lists | Strip list markers | No '- ' or '* ' in output |
| UT-TE-007 | test_extract_txt | Extract text from .txt file | Raw text content |
| UT-TE-008 | test_extract_txt_utf8 | Handle UTF-8 encoding | No character corruption |
| UT-TE-009 | test_extract_txt_legacy_encoding | Detect and convert legacy encodings | Properly converted text |
| UT-TE-010 | test_extract_pdf | Extract text from PDF | Text content from all pages |
| UT-TE-011 | test_extract_pdf_reading_order | Preserve reading order | Logical text flow |
| UT-TE-012 | test_extract_docx | Extract text from DOCX | Paragraph text |
| UT-TE-013 | test_extract_docx_paragraphs | Extract paragraph content | All paragraphs included |
| UT-TE-014 | test_extract_docx_tables | Extract table content | Table text included |
| UT-TE-015 | test_unsupported_format | Reject unsupported file type | UnsupportedFormatError raised |
| UT-TE-016 | test_file_not_found | Handle missing file | TextExtractionError raised |
| UT-TE-017 | test_empty_file | Handle empty file | Empty string returned |
| UT-TE-018 | test_sanitize_control_chars | Remove control characters | Clean text output |

#### 5.1.2 ChunkManager Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-CM-001 | test_chunk_text_basic | Split text into chunks | Multiple chunks returned |
| UT-CM-002 | test_chunk_max_chars | Respect max character limit | No chunk exceeds 500 chars |
| UT-CM-003 | test_chunk_overlap | Verify overlap between chunks | Overlap ratio ~10% |
| UT-CM-004 | test_chunk_single_paragraph | Single paragraph handling | Single chunk returned |
| UT-CM-005 | test_chunk_multiple_paragraphs | Multiple paragraph handling | Multiple chunks |
| UT-CM-006 | test_chunk_empty_text | Handle empty input | Empty list returned |
| UT-CM-007 | test_chunk_very_long_text | Handle very long text | Multiple chunks created |
| UT-CM-008 | test_chunk_silence_markers | Add silence markers | Marked chunks with metadata |
| UT-CM-009 | test_chunk_first_chunk_no_silence | First chunk has no silence | has_silence_before=False |
| UT-CM-010 | test_chunk_other_chunks_have_silence | Other chunks have silence | has_silence_before=True |

#### 5.1.3 TTSClient Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-TTC-001 | test_generate_speech_success | Successful TTS request | Audio bytes returned |
| UT-TTC-002 | test_generate_speech_with_voice_config | Voice customization | Voice config in request |
| UT-TTC-003 | test_generate_speech_api_error_4xx | Handle 4xx errors | TTSAPIError raised |
| UT-TTC-004 | test_generate_speech_api_error_5xx | Handle 5xx errors | Retry triggered |
| UT-TTC-005 | test_generate_speech_retry_success | Retry on failure | Success after retry |
| UT-TTC-006 | test_generate_speech_max_retries | Exhaust all retries | TTSAPIError after max retries |
| UT-TTC-007 | test_generate_speech_rate_limit | Handle 429 rate limit | Retry with retry_after |
| UT-TTC-008 | test_generate_speech_network_error | Handle network errors | Retry triggered |
| UT-TTC-009 | test_exponential_backoff | Verify backoff calculation | Correct delay times |
| UT-TTC-010 | test_exponential_backoff_with_jitter | Verify jitter added | Non-deterministic delays |
| UT-TTC-011 | test_context_manager_enter | Async context manager enter | Session created |
| UT-TTC-012 | test_context_manager_exit | Async context manager exit | Session closed |

#### 5.1.4 AudioStitcher Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-AS-001 | test_stitch_two_files | Stitch two WAV files | Single output file |
| UT-AS-002 | test_stitch_multiple_files | Stitch multiple WAV files | Single output file |
| UT-AS-003 | test_stitch_with_silence | Add silence between chunks | 500ms silence inserted |
| UT-AS-004 | test_stitch_no_silence | Skip silence insertion | No silence added |
| UT-AS-005 | test_generate_silence | Generate silence file | Valid WAV file created |
| UT-AS-006 | test_normalize_audio | Apply loudness normalization | Normalized output |
| UT-AS-007 | test_normalize_audio_default_params | Default normalization params | I=-16, TP=-2, LRA=11 |
| UT-AS-008 | test_stitch_ffmpeg_error | Handle ffmpeg failure | AudioProcessingError raised |
| UT-AS-009 | test_cleanup_concat_list | Remove concat list file | File deleted after stitch |
| UT-AS-010 | test_still_file_exists | Handle existing output file | Overwrite with -y flag |

#### 5.1.5 OutputManager Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-OM-001 | test_save_wav | Save WAV file | File created in output dir |
| UT-OM-002 | test_save_wav_naming | Verify file naming | {name}_{timestamp}.wav |
| UT-OM-003 | test_save_sidecar | Save metadata JSON | Sidecar file created |
| UT-OM-004 | test_sidecar_content | Verify sidecar content | All required fields present |
| UT-OM-005 | test_sidecar_duration | Include duration | duration_seconds field |
| UT-OM-006 | test_sidecar_word_count | Include word count | word_count field |
| UT-OM-007 | test_sidecar_chunk_count | Include chunk count | chunk_count field |
| UT-OM-008 | test_sidecar_voice_config | Include voice config | voice_config field |
| UT-OM-009 | test_sidecar_source_file | Include source file | source_file field |
| UT-OM-010 | test_sidecar_processing_status | Include processing status | processing_status field |
| UT-OM-011 | test_move_to_processed | Move file to processed dir | File moved successfully |
| UT-OM-012 | test_move_to_processed_no_dir | Handle missing processed dir | Create directory |
| UT-OM-013 | test_output_dir_creation | Create output directory | Directory created |

#### 5.1.6 FileWatcher Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-FW-001 | test_start_watcher | Start file monitoring | Watcher started |
| UT-FW-002 | test_stop_watcher | Stop file monitoring | Watcher stopped |
| UT-FW-003 | test_register_callback | Register event handler | Callback registered |
| UT-FW-004 | test_close_write_event | Handle CLOSE_WRITE event | Callback invoked |
| UT-FW-005 | test_modify_event | Handle MODIFY event | Ignored (not CLOSE_WRITE) |
| UT-FW-006 | test_watch_directory | Watch input directory | Directory added to watch |
| UT-FW-007 | test_invalid_directory | Handle invalid directory | Error raised |
| UT-FW-008 | test_nonexistent_directory | Handle nonexistent directory | Error raised |

#### 5.1.7 Config Unit Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-CFG-001 | test_config_defaults | Verify default values | All defaults correct |
| UT-CFG-002 | test_config_from_env | Load from environment | Values from env vars |
| UT-CFG-003 | test_config_from_file | Load from .env file | Values from file |
| UT-CFG-004 | test_config_tts_endpoint | TTS endpoint configuration | Correct endpoint |
| UT-CFG-005 | test_config_processing_dirs | Processing directory config | Correct paths |
| UT-CFG-006 | test_config_chunk_settings | Chunk configuration | Correct chunk settings |
| UT-CFG-007 | test_config_parallel_jobs | Parallel job configuration | Correct max jobs |
| UT-CFG-008 | test_config_logging | Logging configuration | Correct log level |
| UT-CFG-009 | test_config_invalid_value | Reject invalid value | ValidationError raised |
| UT-CFG-010 | test_config_negative_value | Reject negative value | ValidationError raised |

### 5.2 Integration Tests

Integration tests validate component interactions and data flow.

#### 5.2.1 Processing Pipeline Integration Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-PP-001 | test_pipeline_markdown_file | Process .md file end-to-end | WAV file created |
| IT-PP-002 | test_pipeline_txt_file | Process .txt file end-to-end | WAV file created |
| IT-PP-003 | test_pipeline_pdf_file | Process .pdf file end-to-end | WAV file created |
| IT-PP-004 | test_pipeline_docx_file | Process .docx file end-to-end | WAV file created |
| IT-PP-005 | test_pipeline_multiple_chunks | File requiring multiple chunks | All chunks processed |
| IT-PP-006 | test_pipeline_audio_stitching | Verify audio stitching | Single WAV file |
| IT-PP-007 | test_pipeline_sidecar_generation | Verify sidecar creation | JSON file created |
| IT-PP-008 | test_pipeline_file_move | Move processed file | File moved to processed dir |
| IT-PP-009 | test_pipeline_concurrent_processing | Process multiple files | All files processed |
| IT-PP-010 | test_pipeline_error_recovery | Handle processing error | Error logged, continue |

#### 5.2.2 TTS API Integration Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-TTC-001 | test_tts_api_connection | Connect to TTS API | Connection successful |
| IT-TTC-002 | test_tts_api_request_format | Verify request format | Correct JSON structure |
| IT-TTC-003 | test_tts_api_response_format | Verify response format | Correct JSON structure |
| IT-TTC-004 | test_tts_api_audio_data | Verify audio data | Valid WAV bytes |
| IT-TTC-005 | test_tts_api_duration | Verify duration field | Accurate duration |
| IT-TTC-006 | test_tts_api_voice_cloning | Test voice cloning | Cloned voice output |
| IT-TTC-007 | test_tts_api_voice_design | Test voice design | Designed voice output |

#### 5.2.3 File Watcher Integration Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-FW-001 | test_watcher_detects_new_file | Detect new file in input dir | File processing triggered |
| IT-FW-002 | test_watcher_respects_close_write | Wait for CLOSE_WRITE | File fully written |
| IT-FW-003 | test_watcher_multiple_files | Handle multiple files | All files processed |
| IT-FW-004 | test_watcher_file_deletion | Handle file deletion | Ignored (not in scope) |
| IT-FW-005 | test_watcher_directory_rename | Handle directory rename | Ignored (not in scope) |

#### 5.2.4 Audio Stitcher Integration Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-AS-001 | test_stitch_real_wav_files | Stitch real WAV files | Valid output |
| IT-AS-002 | test_still_silence_insertion | Insert silence between files | Silence present |
| IT-AS-003 | test_still_audio_normalization | Normalize audio levels | Consistent volume |
| IT-AS-004 | test_still_large_file | Handle large file | Processing completes |

### 5.3 End-to-End Tests

E2E tests validate the complete user journey.

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| E2E-001 | test_full_pipeline_markdown | Complete pipeline with .md | WAV + sidecar created |
| E2E-002 | test_full_pipeline_pdf | Complete pipeline with .pdf | WAV + sidecar created |
| E2E-003 | test_full_pipeline_txt | Complete pipeline with .txt | WAV + sidecar created |
| E2E-004 | test_full_pipeline_docx | Complete pipeline with .docx | WAV + sidecar created |
| E2E-005 | test_full_pipeline_large_file | Large file processing | Processing completes |
| E2E-006 | test_full_pipeline_systemd_path | Systemd path unit integration | Service triggered |
| E2E-007 | test_full_pipeline_concurrent | Multiple concurrent files | All processed |
| E2E-008 | test_full_pipeline_restart_recovery | Restart during processing | Resume from checkpoint |

### 5.4 Negative Tests

Negative tests validate error handling and robustness.

#### 5.4.1 Invalid Input Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| NT-001 | test_invalid_file_extension | Unsupported file type | Error logged, file skipped |
| NT-002 | test_empty_file | Empty input file | Error logged, file skipped |
| NT-003 | test_corrupted_pdf | Corrupted PDF file | Error logged, file skipped |
| NT-004 | test_corrupted_docx | Corrupted DOCX file | Error logged, file skipped |
| NT-005 | test_path_traversal | Path traversal attempt | Error raised, file rejected |
| NT-006 | test_file_too_large | File exceeds size limit | Error raised, file rejected |
| NT-007 | test_invalid_encoding | Invalid encoding | Error raised, file rejected |
| NT-008 | test_binary_file_as_text | Binary file treated as text | Error raised |

#### 5.4.2 API Failure Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| NT-009 | test_tts_api_unavailable | TTS API down | Retry with backoff, then fail |
| NT-010 | test_tts_api_rate_limit | Rate limit hit | Retry with retry_after |
| NT-011 | test_tts_api_invalid_response | Invalid API response | Error raised |
| NT-012 | test_tts_api_timeout | API timeout | Retry with backoff |
| NT-013 | test_network_error | Network failure | Retry with backoff |

#### 5.4.3 System Error Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| NT-014 | test_disk_full | Disk space exhausted | Error raised, processing halted |
| NT-015 | test_no_write_permissions | No write permissions | Error raised |
| NT-016 | test_ffmpeg_not_installed | ffmpeg missing | Error raised |
| NT-017 | test_temp_dir_unavailable | Temp directory unavailable | Error raised |

### 5.5 Performance Tests

Performance tests validate SLA compliance.

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| PT-001 | test_throughput_baseline | Baseline throughput measurement | 2 min audio / 1 min processing |
| PT-002 | test_throughput_max_parallel | Max parallel processing | MAX_PARALLEL files concurrent |
| PT-003 | test_api_latency_healthy | Healthy API latency | < 200ms |
| PT-004 | test_api_latency_degraded | Degraded API latency | < 500ms |
| PT-005 | test_memory_usage_single | Memory usage per file | < 256MB |
| PT-006 | test_memory_usage_concurrent | Memory usage concurrent | < 512MB |
| PT-007 | test_startup_time | Service startup time | < 5 seconds |
| PT-008 | test_file_watcher_latency | File detection latency | < 1 second |
| PT-009 | test_audio_stitching_time | Audio stitching time | Proportional to audio length |
| PT-010 | test_large_file_processing | Large file processing | Completes without OOM |

### 5.6 Security Tests

Security tests validate input validation and protection.

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| ST-001 | test_path_traversal_basic | Basic path traversal | Rejected |
| ST-002 | test_path_traversal_encoded | Encoded path traversal | Rejected |
| ST-003 | test_path_traversal_double_encoded | Double-encoded traversal | Rejected |
| ST-004 | test_null_byte_injection | Null byte injection | Rejected |
| ST-005 | test_control_char_injection | Control character injection | Stripped |
| ST-006 | test_html_injection | HTML injection attempt | Stripped |
| ST-007 | test_script_injection | Script injection attempt | Stripped |
| ST-008 | test_sql_injection | SQL injection attempt | Stripped (if applicable) |
| ST-009 | test_file_size_bypass | File size bypass attempt | Rejected |
| ST-010 | test_symlink_attack | Symlink attack | Rejected |

---

## 6. Risk-Adjusted Testing Strategy

### 6.1 Risk Assessment Matrix

| Component | Risk Level | Business Impact | Testing Depth |
|-----------|------------|-----------------|---------------|
| TextExtractor | High | Core functionality | Deep testing (all formats, edge cases) |
| ChunkManager | Medium | Audio quality | Deep testing (boundary conditions) |
| TTSClient | High | Core functionality | Deep testing (all error paths) |
| AudioStitcher | Medium | Output quality | Medium testing (common paths) |
| OutputManager | Low | Metadata | Light testing (happy path) |
| FileWatcher | Medium | Reliability | Medium testing (edge cases) |
| Systemd Integration | Low | Deployment | Light testing (integration) |

### 6.2 Testing Priority

**Priority 1 (Critical - Must Pass):**
- All unit tests for TextExtractor
- All unit tests for TTSClient
- Integration tests for processing pipeline
- E2E tests for all file formats
- Negative tests for API failures

**Priority 2 (High - Should Pass):**
- All unit tests for ChunkManager
- Integration tests for audio stitching
- Performance tests for throughput
- Security tests for input validation

**Priority 3 (Medium - Nice to Have):**
- Unit tests for OutputManager
- Integration tests for file watcher
- Performance tests for memory usage

**Priority 4 (Low - Future):**
- All unit tests for FileWatcher
- Performance benchmark tests
- All security penetration tests

### 6.3 Defect Severity Classification

| Severity | Definition | Release Decision |
|----------|------------|------------------|
| SEV-0 | System crash, data loss | Blocker - No release |
| SEV-1 | Core functionality broken | Blocker - No release |
| SEV-2 | Major feature broken | Blocker - No release |
| SEV-3 | Minor feature broken | Warning - Release with exception |
| SEV-4 | Cosmetic issue | Informational - Release |

---

## 7. Defect Lifecycle Management

### 7.1 Defect Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   NEW       │────▶│   OPEN      │────▶│   IN PROGRESS │
└─────────────┘     └─────────────┘     └─────────────┘
                                                      │
                                                      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   VERIFIED  │◀────│   READY FOR │◀────│   CODE REVIEW │
│             │     │   RELEASE   │     └─────────────┘
└─────────────┘     └─────────────┘
        │
        ▼
┌─────────────┐
│   CLOSED    │
└─────────────┘
```

### 7.2 Defect Triage Process

1. **Initial Triage**: Within 24 hours of discovery
2. **Severity Assignment**: Based on impact assessment
3. **Root Cause Analysis**: For SEV-0 and SEV-1 defects
4. **Fix Planning**: For all defects
5. **Verification**: After fix deployment
6. **Closure**: With documentation

### 7.3 Bug Bar Policy

**Release Blockers (Must Fix Before Release):**
- SEV-0 defects (crashes, data loss)
- SEV-1 defects (core functionality broken)
- SEV-2 defects (major feature broken)
- Security vulnerabilities (any severity)
- Performance regressions > 20%

**Technical Debt (Can Be Deferred):**
- SEV-3 defects (minor feature broken)
- SEV-4 defects (cosmetic issues)
- Performance improvements (non-regression)
- Code quality improvements

---

## 8. Test Data Management

### 8.1 Test Data Categories

| Category | Description | Storage |
|----------|-------------|---------|
| Static Fixtures | Pre-generated test files | tests/fixtures/ |
| Dynamic Fixtures | Generated during test execution | temp directories |
| Mock Data | Mocked API responses | tests/mocks/ |
| Performance Data | Benchmark data | tests/performance/ |

### 8.2 Fixture Files

```
tests/fixtures/
├── sample.md                    # Basic markdown file
├── sample_markdown.md           # Markdown with all syntax types
├── sample_large.md              # Large file for performance testing
├── sample_multilingual.txt      # UTF-8 multilingual content
├── sample_with_special_chars.txt # Special characters for encoding tests
├── sample_with_tables.docx      # DOCX with tables
├── sample_with_images.pdf       # PDF with images (text extraction only)
├── sample_empty.txt             # Empty file
├── sample_unicode.md            # Unicode content
└── sample_markdown_complex.md   # Complex markdown structure
```

### 8.3 Test Data Generation

```python
# tests/mocks/fixtures.py
import random
import string
from pathlib import Path

def generate_markdown_file(path: Path, size: str = "small") -> Path:
    """Generate a markdown file of specified size."""
    sizes = {
        "small": 1000,
        "medium": 10000,
        "large": 100000
    }
    
    words = [''.join(random.choices(string.ascii_lowercase, k=5)) 
             for _ in range(sizes[size] // 5)]
    
    content = " ".join(words)
    # Add markdown formatting
    content = f"# Title\n\n{content}\n\n## Section\n\n{content}"
    
    path.write_text(content)
    return path

def generate_pdf_file(path: Path) -> Path:
    """Generate a PDF file for testing."""
    # Note: Use a library like reportlab or pre-generated PDF
    pass

def generate_docx_file(path: Path) -> Path:
    """Generate a DOCX file for testing."""
    # Note: Use python-docx to create test document
    pass
```

---

## 9. Performance Testing

### 9.1 Performance Test Scenarios

| Scenario | Configuration | Expected Result |
|----------|---------------|-----------------|
| Single file processing | 1 parallel job | Baseline throughput |
| Max parallel processing | MAX_PARALLEL jobs | Throughput scaling |
| Large file processing | 100KB+ file | No OOM, reasonable time |
| Continuous processing | 100 files in queue | Steady state throughput |
| API degradation | 500ms API latency | Graceful degradation |
| API failure | 100% API failures | Proper error handling |

### 9.2 Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Throughput | 2 min audio / 1 min processing | Time measurement |
| API Latency (healthy) | < 200ms | Network timing |
| API Latency (degraded) | < 500ms | Network timing |
| Memory Usage (single) | < 256MB | Memory profiling |
| Memory Usage (concurrent) | < 512MB | Memory profiling |
| Startup Time | < 5 seconds | Service start measurement |
| File Detection Latency | < 1 second | inotify timing |

### 9.3 Performance Test Execution

```python
# tests/performance/test_throughput.py
import pytest
import time
from pathlib import Path

class TestThroughput:
    @pytest.mark.benchmark
    def test_throughput_baseline(self, temp_dir, mock_config):
        """Test baseline throughput with single file."""
        # Setup
        input_file = temp_dir / "input" / "test.md"
        input_file.parent.mkdir()
        input_file.write_text("Test content. " * 1000)
        
        # Measure
        start = time.time()
        # Execute pipeline
        end = time.time()
        
        # Assert
        processing_time = end - start
        assert processing_time < expected_time, f"Throughput: {processing_time}s"
    
    @pytest.mark.benchmark
    def test_throughput_max_parallel(self, temp_dir, mock_config):
        """Test throughput with max parallel processing."""
        # Setup multiple files
        files = [temp_dir / "input" / f"test{i}.md" for i in range(10)]
        for f in files:
            f.parent.mkdir()
            f.write_text("Test content. " * 1000)
        
        # Measure concurrent processing
        start = time.time()
        # Execute concurrent pipeline
        end = time.time()
        
        # Assert
        concurrent_time = end - start
        assert concurrent_time < single_time * 0.5, "Parallelism not effective"
```

---

## 10. Security Testing

### 10.1 Security Test Scenarios

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Path traversal | `/etc/passwd` | Rejected |
| Path traversal | `../../../etc/passwd` | Rejected |
| Path traversal | `..%2F..%2Fetc%2Fpasswd` | Rejected |
| Null byte injection | `file.txt%00.md` | Rejected |
| Control characters | `text\x00\x01\x02` | Stripped |
| HTML injection | `<script>alert(1)</script>` | Stripped |
| XSS attempt | `<img onerror=alert(1)>` | Stripped |
| File size bypass | Large file (>10MB) | Rejected |
| Symlink attack | Symlink to /etc | Rejected |

### 10.2 Security Test Implementation

```python
# tests/security/test_input_validation.py
import pytest
from pathlib import Path
from myaudible.core.text_extractor import TextExtractor
from myaudible.exceptions import UnsupportedFormatError

class TestInputValidation:
    @pytest.fixture
    def extractor(self):
        return TextExtractor()
    
    @pytest.mark.asyncio
    async def test_path_traversal_basic(self, temp_dir, extractor):
        """Test path traversal with basic .."""
        malicious_path = temp_dir / ".." / ".." / "etc" / "passwd"
        malicious_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pytest.raises(ValueError):
            await extractor.extract(malicious_path)
    
    @pytest.mark.asyncio
    async def test_path_traversal_encoded(self, temp_dir, extractor):
        """Test path traversal with URL encoding."""
        # Note: Path traversal should be detected before URL decoding
        pass
    
    @pytest.mark.asyncio
    async def test_null_byte_injection(self, temp_dir, extractor):
        """Test null byte injection in filename."""
        malicious_path = temp_dir / "file.txt\x00.md"
        malicious_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pytest.raises(ValueError):
            await extractor.extract(malicious_path)
    
    @pytest.mark.asyncio
    async def test_file_too_large(self, temp_dir, extractor):
        """Test file size limit enforcement."""
        large_file = temp_dir / "large.txt"
        large_file.write_text("x" * (11 * 1024 * 1024))  # 11MB
        
        with pytest.raises(ValueError):
            await extractor.extract(large_file)
```

---

## 11. Test Environment Setup

### 11.1 Prerequisites

```bash
# System dependencies
sudo apt-get install -y python3.9 python3.9-venv ffmpeg systemd libinotify-dev

# Python dependencies
pip install pytest pytest-asyncio pytest-cov pytest-benchmark
pip install aiohttp python-docx pdfplumber semchunk ffmpeg-python
pip install pydantic pydantic-settings structlog
```

### 11.2 Environment Configuration

```bash
# .env.test
MYAUDIBLE_TTS_ENDPOINT=http://localhost:8008/v1/audio/speech
MYAUDABLE_PROCESSING_INPUT_DIR=/tmp/test-input
MYAUDABLE_PROCESSING_OUTPUT_DIR=/tmp/test-output
MYAUDABLE_PROCESSING_PROCESSED_DIR=/tmp/test-processed
MYAUDABLE_PROCESSING_CHUNK_MAX_CHARS=500
MYAUDABLE_PROCESSING_CHUNK_OVERLAP_RATIO=0.1
MYAUDABLE_PROCESSING_MAX_PARALLEL_JOBS=2
MYAUDABLE_LOGGING_LEVEL=DEBUG
```

### 11.3 Test Execution Commands

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run E2E tests only
pytest tests/e2e/ -v

# Run with coverage
pytest tests/ --cov=myaudible --cov-report=html --cov-report=term-missing

# Run performance tests
pytest tests/performance/ -v --benchmark-save=results

# Run security tests
pytest tests/security/ -v

# Run specific test
pytest tests/unit/test_text_extractor.py::test_extract_markdown -v
```

### 11.4 CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=myaudible --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/integration/ -v
      
      - name: Run E2E tests
        run: pytest tests/e2e/ -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 12. Test Execution Plan

### 12.1 Phase 1: Foundation (Week 1)

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 1 | Set up test infrastructure | pytest config, fixtures |
| 2 | Implement unit tests for TextExtractor | 18 unit tests |
| 3 | Implement unit tests for ChunkManager | 10 unit tests |
| 4 | Implement unit tests for TTSClient | 12 unit tests |
| 5 | Implement unit tests for AudioStitcher | 10 unit tests |

### 12.2 Phase 2: Integration (Week 2)

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 1 | Implement integration tests for pipeline | 10 integration tests |
| 2 | Implement integration tests for TTS API | 7 integration tests |
| 3 | Implement integration tests for file watcher | 5 integration tests |
| 4 | Implement negative tests | 17 negative tests |
| 5 | Implement security tests | 10 security tests |

### 12.3 Phase 3: E2E & Performance (Week 3)

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 1 | Implement E2E tests | 8 E2E tests |
| 2 | Implement performance tests | 10 performance tests |
| 3 | Run full test suite | Coverage report |
| 4 | Performance benchmarking | Benchmark results |
| 5 | Defect triage and fixes | Bug backlog |

### 12.4 Phase 4: Validation (Week 4)

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 1 | Regression testing | Full test suite pass |
| 2 | Performance validation | SLA compliance |
| 3 | Security validation | Security audit |
| 4 | Documentation | Test documentation |
| 5 | Release readiness review | Go/No-Go decision |

---

## 13. Acceptance Criteria

### 13.1 Code Coverage Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Line Coverage | 80%+ | pytest-cov |
| Branch Coverage | 75%+ | pytest-cov |
| Function Coverage | 85%+ | pytest-cov |
| Unit Test Coverage | 100% of core components | Manual verification |

### 13.2 Test Execution Requirements

| Requirement | Target |
|-------------|--------|
| All unit tests passing | 100% |
| All integration tests passing | 100% |
| All E2E tests passing | 100% |
| All negative tests passing | 100% |
| All security tests passing | 100% |
| All performance tests passing | 100% |

### 13.3 Defect Requirements

| Severity | Maximum Allowed |
|----------|-----------------|
| SEV-0 | 0 |
| SEV-1 | 0 |
| SEV-2 | 0 |
| SEV-3 | 3 |
| SEV-4 | 10 |

### 13.4 Performance Requirements

| Metric | Target |
|--------|--------|
| Throughput | 2 min audio / 1 min processing |
| API Latency (healthy) | < 200ms |
| Startup Time | < 5 seconds |
| Memory Usage (single) | < 256MB |
| Memory Usage (concurrent) | < 512MB |

### 13.5 Documentation Requirements

- [ ] Test plan document complete
- [ ] Unit test documentation complete
- [ ] Integration test documentation complete
- [ ] E2E test documentation complete
- [ ] Performance test documentation complete
- [ ] Security test documentation complete
- [ ] Test data documentation complete
- [ ] CI/CD pipeline configured

---

## 14. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| Chunk | A paragraph-sized segment of text sent to the TTS API |
| Sidecar | A JSON metadata file generated alongside the output WAV |
| Path Unit | A systemd unit file that monitors directory changes |
| Inotify | Linux kernel subsystem for file system events |
| Exponential Backoff | Retry strategy with increasing delays |
| Golden Dataset | Set of constraints defining expected behavior |
| Bug Bar | Standard for defect acceptance |

### B. References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/)
- [Qwen 3.0 TTS API Documentation](http://192.168.1.104:8008/docs)
- [semchunk Library](https://github.com/example/semchunk)
- [pdfplumber Documentation](https://pdfplumber.readthedocs.io/)
- [python-docx Documentation](https://python-docx.readthedocs.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Systemd Path Units](https://www.freedesktop.org/software/systemd/man/systemd.path.html)

### C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-04-19 | Test Lead | Initial test plan |

### D. Test Plan Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Test Lead | | | |
| Development Lead | | | |
| Product Owner | | | |
| QA Manager | | | |

---

*This test plan is a living document and should be updated as the project evolves.*
