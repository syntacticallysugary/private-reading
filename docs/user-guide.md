# myAudible User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start Guide](#quick-start-guide)
5. [Core Concepts](#core-concepts)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Getting Started

myAudible is a powerful tool for processing audio file descriptions. This guide will help you set up and use the application.

### Prerequisites

Before using myAudible, ensure you have:

- Python 3.10+ installed
- pip (Python package manager)
- A Qwen 3.0 TTS API account (or compatible TTS API)

---

## Installation

### Step 1: Setup Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages:
- aiohttp
- pdfplumber
- python-docx
- semchunk
- ffmpeg-python
- scipy
- pydantic-settings
- structlog
- pytest and testing tools

### Step 3: Install myAudible

```bash
pip install -e .
```

---

## Configuration

### Using Environment Variables

Create a `.env` file in the project root:

```env
# TTS API Configuration
TTS_API_URL=https://api.qwen3.0.ai/tts
TTS_API_KEY=your-api-key
TTS_API_VOICE_DESIG=coral

# Processing Settings
TTS_CHUNKS_DELAY=3000.0
TTS_RETRY_COUNT=3
TTS_TIMEOUT=30.0

# Output Configuration
OUTPUT_PATH=output
```

### Using Config File

Create `config/settings.json`:

```json
{
  "tts": {
    "api_url": "https://api.qwen3.0.ai/tts",
    "api_key": "your-api-key",
    "voice_designator": "coral",
    "chunks_delay": 3000.0,
    "retry_count": 3,
    "timeout": 30.0
  },
  "processing": {
    "ignore_encoding_errors": false
  },
  "logging": {
    "level": "INFO"
  }
}
```

---

## Quick Start Guide

### CLI Usage

```bash
# Process a single file
python -m myaudible --input input.md --output output.json

# Process from current directory
python -m myaudible --input document.md
```

### Programmatic Usage

Basic example:

```python
from myaudible import app as myaudible
from myaudible.config import AppConfig
from pathlib import Path

# Initialize configuration
config = AppConfig(
    tts_api_url="https://api.qwen3.0.ai/tts",
    tts_api_key="your-api-key",
    tts_api_voice_desig="coral",
    tts_chunks_delay="3000.0",
    tts_retry_count=3,
    tts_timeout=30.0,
)

# Create application instance
app_instance = myaudible.MyAudibleApp(config)

# Process a file
result = await app_instance.process_single_file(Path("document.md"))

# Access results
print(f"Text extracted: {len(result.text)} characters")
print(f"Chunks created: {len(result.chunks)}")
```

---

## Core Concepts

### Understanding the Pipeline

myAudible processes files through a series of steps:

```
┌─────────────────┐
│   Text Input    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Text Extract   │
│  (mime-detect)  │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   Text         ─┼─── Single chunk
│    Chunked      ─┼─── Multiple chunks
│    (overlap)    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Audio         ─┼─── No stitching
│     Stitch      ─┼─── Combined audio
│    (optional)   │
└─────────────────┘
```

#### Step 1: File Detection

myAudible automatically detects the file format:

- `.md` / `.markdown` → Markdown
- `.txt` / `.text` → Plain Text
- `.docx` / `.doc` → Word Document
- `.pdf` → PDF File (PDF requires pdfplumber)

#### Step 2: Text Extraction

Text content is extracted from the file while preserving formatting:

- **Markdown**: Headers, bullet points, inline code blocks
- **Plain text**: Line-by-line processing
- **DOCX**: Paragraph-by-paragraph extraction
- **PDF**: Page-by-page reading order

#### Step 3: Semantic Chunking

Text is divided into semantic chunks using the `semchunk` algorithm:

```python
chunks = [
    "This is the first paragraph.",
    "This is the second paragraph.",
    "This is the third paragraph."
]
```

#### Step 4: Sleep Markers

Silence markers are added between chunks:

```python
chunks_with_markers = [
    {"text": "First chunk", "series_index": "0"},
    {"text": "Second chunk", "series_index": "1"},
    {"text": "Third chunk", "series_index": "2"}
]
```

#### Step 5: Audio Stitching

Multiple audio chunks are combined into one:

```python
final_audio = stitcher.stitch(wav_files)
```

---

## Advanced Usage

### Customizing Text Extraction

Extract text with custom configurations:

```python
from myaudible.core.text_extractor import TextExtractor
from pathlib import Path

extractor = TextExtractor()

# Extract from markdown
with open("document.md", "r", encoding="utf-8") as f:
    text = await extractor.extract(Path("document.md"))
```

### Advanced Chunking Options

Control chunk behavior:

```python
from myaudible.core.chunk_manager import ChunkManager, ChunkConfig
from pathlib import Path

manager = ChunkManager()
config = ChunkConfig(
    max_chars=500,
    overlap=50,
    max_paragraphs=3
)

text = "Your text content here..."
chunks = await manager.chunk(text)
```

### Custom TTS Configuration

```python
from myaudible.core.tts_client import TTSClient
from myaudible.core.text_extractor import TextExtractor
from myaudible.config import TTSConfig
from pathlib import Path

# Initialize TTS client
voice_config = TTSConfig(
    api_url="https://api.qwen3.0.ai/tts",
    api_key="your-api-key",
    voice_designator="coral"
)

client = TTSClient(
    tts_api_url="https://api.qwen3.0.ai/tts",
    tts_api_key="your-api-key",
    tts_api_voice_designator="coral"
)

# Generate speech
async with client:
    audio_path = await client.generate_speech(
        ref_text=text,
        voice_design="coral",
        duration="4.0",
        notch=False,
        ref_audio_format="wav",
        ref_audio_path=None
    )
```

---

## Command-Line Reference

### Basic Options

```bash
python -m myaudible --help
# Show available CLI options
```

### Input Options

```bash
python -m myaudible --input input.md               # Input file path
python -m myaudible --input-dir ./my-documents/     # Directory as output bas
```

### Output Options

```bash
python -m myaudible --output output.json            # Output file path
python -m myaudible --output-dir ./output/         # Output directory
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Text Extraction Fails

**Symptom**: Text is empty or minimal

**Solutions**:
1. Check file encoding: `open("file", "r", encoding="utf-8-sig")`
2. Verify file format is supported
3. Check pdfplumber is installed for PDFs: `pip install pdfplumber`
4. Check python-docx is installed for DOCX: `pip install python-docx`

#### Issue 2: TTS Generation Fails

**Symptom**: TTS API doesn't respond or returns errors

**Solutions**:
1. Verify API key is valid
2. Check network connectivity
3. Reduce `tts_timeout`: `tts_timeout=60.0`
4. Increase retry count: `tts_retry_count=5`

#### Issue 3: Chunking Produces Too Many/Too Few Chunks

**Symptom**: Each chunk is too small or text is too large

**Solutions**:

To reduce number of chunks:
```python
config = ChunkConfig(max_chars=1000, overlap=200)
```

To increase number of chunks:
```python
config = ChunkConfig(max_chars=300, overlap=50)
```

#### Issue 4: Audio Stitching Fails

**Symptom**: FFmpeg command fails during stitching

**Solutions**:
1. Verify ffmpeg is installed: `ffmpeg -version`
2. Check path to ffmpeg executable
3. Reduce chunk count for smaller files

---

## Best Practices

### 1. Error Handling

```python
from pathlib import Path
from myaudible import app as myaudible
from myaudible.config import AppConfig

config = AppConfig(
    tts_api_url="https://api.qwen3.0.ai/tts",
    tts_api_key="your-api-key",
)

app_instance = myaudible.MyAudibleApp(config)

async def process_file(file_path: Path) -> dict:
    """Process with error handling."""
    try:
        result = await app_instance.process_single_file(file_path)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### 2. Logging Results

```python
from myaudible.core.output_manager import OutputManager
from pathlib import Path

output_manager = OutputManager()

result = await process_single_file(file_path)

# Write to file
output_file = Path("./output.json")
output_manager.write_output(output_file, result)

# Read back
with open(output_file, "r", encoding="utf-8") as f:
    read_result = json.load(f)
```

### 3. Batch Processing

```python
from myaudible import app as myaudible
from myaudible.config import AppConfig
from pathlib import Path
import asyncio

config = AppConfig(...)
app_instance = myaudible.MyAudibleApp(config)

async def batch_process(file_paths: list[Path]):
    """Process multiple files in sequence."""
    results = []
    for file_path in file_paths:
        result = await app_instance.process_single_file(file_path)
        results.append(result)
    return results

# Process files
file_paths = [Path("doc1.md"), Path("doc2.md"), Path("doc3.md")]
batch_results = asyncio.create_task(batch_process(file_paths))
```

### 4. Performance Monitoring

```python
import time

async def process_with_timing(input_file: Path):
    """Process file with timing."""
    start_time = time.time()
    
    result = await app_instance.process_single_file(input_file)
    
    elapsed = time.time() - start_time
    
    return {
        "result": result,
        "processing_time_seconds": elapsed,
        "file_size_bytes": input_file.stat().st_size
    }
```

---

## Appendix

### Supported File Formats

| Extension | Format | Required Package |
|-----------|--------|------------------|
| `.md` | Markdown | None |
| `.txt` | Plain Text | None |
| `.docx` | Word Document | python-docx |
| `.pdf` | PDF | pdfplumber |

### Voice Designators

Qwen 3.0 TTS supports various voice designs:

- `coral` - Default female voice
- `bowen` - Default male voice
- `aditi` - Sharp female voice
- `kunge` - Deep male voice

### Output Format

JSON output structure:

```json
{
  "file_path": "input.md",
  "text": "Extracted text content...",
  "chunks": ["Chunk 1", "Chunk 2"],
  "chunk_entries": [
    {"text": "Chunk 1", "series_index": "0"},
    {"text": "Chunk 2", "series_index": "1"}
  ]
}
```

---

For more information, see the [API Reference](../docs/api-reference.md) or visit the project documentation.
