# myAudible API Reference

## Table of Contents

1. [Configuration API](#configuration-api)
2. [Core Module API](#core_module_api)
3. [Data Models](#data_models)
4. [Application API](#application_api)

---

## Configuration API

### `AppConfig`

Main application configuration class that aggregates all settings.

```python
from myaudible.config import AppConfig
from pydantic import Field
from typing import Any, Optional

class AppConfig(BaseSettings):
    """Application configuration."""
    
    # Environment variables
    env_file: Optional[str] = None
    
    # TTS settings
    tts_api_url: str
    tts_api_key: str
    tts_api_voice_desig: str
    tts_chunks_delay: str = "3000.0"
    tts_retry_count: int = 3
    tts_timeout: float = 30.0
    
    # Processing settings
    tts_api_key_file: Optional[str] = None
```

#### Properties

- `tts_config`: `TTSConfig` - TTS API settings
- `processing_config`: `ProcessingConfig` - Text processing settings  
- `logging_config`: `LoggingConfig` - Logging settings
- `get(key, default)`: `Any` - Dynamic configuration access

---

## Core Module API

### `TextExtractor`

```python
from pathlib import Path
from myaudible.core.text_extractor import TextExtractor

extractor = TextExtractor()

# Extract text from file
raw_text = await extractor.extract(file_path)  # str
```

#### Methods

| Method | Description | Return Type |
|--------|-------------|-------------|
| `extract(file_path)` | Extract text from a file by detecting its format | `str` |
| `_extract_markdown(file_path)` | Extract text from markdown files | `str` |
| `_extract_pdf(file_path)` | Extract text from PDF files | `str` |
| `_extract_txt(file_path)` | Extract text from plain text files | `str` |
| `_extract_docx(file_path)` | Extract text from DOCX files | `str` |

---

### `ChunkManager`

```python
from pathlib import Path
from myaudible.core.chunk_manager import ChunkManager

manager = ChunkManager()

# Chunk text into semantic chunks
chunked_text = await manager.chunk(text)  # List[str]

# Get chunk entries with series numbers
chunk_entries = await manager.add_silence_markers(chunks)  # List[dict]
```

#### Methods

| Method | Description | Return Type |
|--------|-------------|-------------|
| `chunk(text)` | Split text into semantic chunks | `List[str]` |
| `add_silence_markers(chunks)` | Add silence markers to chunks | `List[dict]` |
| `calculate_overlap()` | Calculate optimal overlap between chunks | `int` |

---

### `AudioStitcher`

```python
from pathlib import Path
from myaudible.core.audio_stitcher import AudioStitcher

stitcher = AudioStitcher()

# Stitch multiple audio files together
result_path = await stitcher.stitch(wav_files)  # Path
```

#### Methods

| Method | Description | Return Type |
|--------|-------------|-------------|
| `stitch(wav_files)` | Stitch multiple audio files | `Path` |
| `add_silence(wav_file, duration)` | Add silence to audio file | `Path` |
| `normalize_audio(wav_file)` | Normalize audio file | `Path` |

---

### `TTSClient`

```python
from myaudible.core.tts_client import TTSClient

client = TTSClient(
    api_url="...",
    api_key="...",
    voice_designator="..."
)

# Use as async context manager
async with client:
    # Generate speech
    audio_path = await client.generate_speech(
        ref_text="This is my text",
        voice_design="coral",
        duration="4.0"
    )  # Path
```

#### Methods

| Method | Description | Return Type |
|--------|-------------|-------------|
| `__aenter__()` | Initialize aiohttp session | `TTSClient` |
| `__aexit__()` | Close session | `None` |
| `generate_speech(ref_text, voice_design, duration, ref_audio, ref_audio_format)` | Generate speech from text | `Path` |
| `_do_generate()` | Internal TTS API request | `Path` |
| `_handle_retry(status_code)` | Handle retry logic | `None` |
| `calculate_backoff(attempt)` | Calculate backoff delay | `float` |

---

## Data Models

### `ProcessingResult`

```python
from myaudible.models import ProcessingResult

result = await process_file(file_path)
result.file_path      # Path
result.text           # str
result.chunks         # List[str]
result.chunk_entries  # List[dict]
```

#### Fields

| Field | Type | Description |
|--------|------|-------------|
| `file_path` | `Path` | Input file path |
| `text` | `str` | Extracted raw text |
| `chunks` | `List[str]` | Chunked text segments |
| `chunk_entries` | `List[dict]` | Chunks with silence markers |

---

### `Job`

```python
from myaudible.models import Job

job = Job(file_path="input.md", priority=1)
```

#### Fields

| Field | Type | Description |
|--------|------|-------------|
| `file_path` | `Path` | Input file path |
| `priority` | `int` | Job priority |
| `created_at` | `datetime` | Creation timestamp |

---

### `ProcessingStats`

```python
from myaudible.models import ProcessingStats

stats = ProcessingStats(
    total_files=10,
    processed=8,
    failed=2,
    success_rate=80.0,
    avg_processing_time=2.5
)
```

#### Fields

| Field | Type | Description |
|--------|------|-------------|
| `total_files` | `int` | Total files queued |
| `processed` | `int` | Successfully processed |
| `failed` | `int` | Failed processing |
| `success_rate` | `float` | Success percentage |
| `avg_processing_time` | `float` | Average time in seconds |

---

## Application API

### `MyAudibleApp`

```python
from myaudible import app
from myaudible.config import AppConfig

config = AppConfig(...)
application = app.MyAudibleApp(config)
```

#### Methods

| Method | Async | Description | Return Type |
|--------|-------|-------------|-------------|
| `__init__(config)` | No | Initialize application | `MyAudibleApp` |
| `run()` | Yes | Main application loop | `None` |
| `_main_loop()` | Yes | Application main logic | `None` |
| `process_single_file(file_path)` | Yes | Process one file | `ProcessingResult` |
| `health_check()` | No | Check application health | `dict` |
| `_parse_arguments()` | No | Parse CLI arguments | `None` |
| `_setup_logging()` | No | Setup logging | `None` |
| `_log_startup()` | No | Log startup message | `None` |

---

## Exception Handling

### `FileNotFoundError`

```python
from myaudible.exceptions import FileNotFoundError
# Raised when file is not found during processing
```

### `ProcessCompleteException`

```python
from myaudible.exceptions import ProcessCompleteException
# Normal exit condition from process_workflow()
```

### `NoInputException`

```python
from myaudible.exceptions import NoInputException
# Raised when no input is provided
```

### `TTSClientError`

```python
from myaudible.exceptions import TTSClientError
# High level TTS error handling
```

### `ChunkConfigError`

```python
from myaudible.exceptions import ChunkConfigError
# Raised when chunk configuration is invalid
```

---

## Quick Start Examples

### Text Extraction

```python
from myaudible.core.text_extractor import TextExtractor
from pathlib import Path

extractor = TextExtractor()
result = await extractor.extract(Path("document.md"))
print(f"Extracted {len(result)} characters")
```

### Text Chunking

```python
from myaudible.core.chunk_manager import ChunkManager
from myaudible.core.text_extractor import TextExtractor

extractor = TextExtractor()
manager = ChunkManager()

text = await extractor.extract(Path("document.md"))
chunks = await manager.chunk(text)
print(f"Created {len(chunks)} chunks")
```

### TTS Generation

```python
from myaudible.core.tts_client import TTSClient
from myaudible.core.text_extractor import TextExtractor

extractor = TextExtractor()
client = TTSClient(...)

text = await extractor.extract(Path("document.md"))
audio_path = await client.generate_speech(
    ref_text=text,
    voice_design="coral"
)
```

### Full Pipeline

```python
from myaudible import app
from myaudible.config import AppConfig

config = AppConfig(
    tts_api_url="https://api.qwen3.0.ai/tts",
    tts_api_key="your-api-key",
    tts_api_voice_desig="coral",
)

application = app.MyAudibleApp(config)

result = await application.process_single_file(Path("input.md"))
```

---

## Testing

### Unit Tests

```python
# tests/core/test_text_extractor.py
from myaudible.core.text_extractor import TextExtractor
import pytest

@pytest.mark.asyncio
async def test_extract_markdown():
    extractor = TextExtractor()
    result = await extractor.extract(MARKDOWN_FILE)
    assert result is not None
    assert len(result) > 0
```

### Integration Tests

```python
# tests/e2e/test_end_to_end.py
from myaudible import app
from myaudible.config import AppConfig

async def test_full_pipeline():
    config = AppConfig(...)
    application = app.MyAudibleApp(config)
    
    result = await application.process_single_file(
        Path("sample_document.md")
    )
    assert result is not None
    assert result.text is not None
```

---

## License

MIT License
