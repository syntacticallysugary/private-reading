# myAudible - Design Document

## Document Information

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0.0 | 2026-04-19 | Initial | Draft |

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [API Specifications](#api-specifications)
6. [Database Schema](#database-schema)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Security](#security)
10. [Deployment](#deployment)
11. [Testing Strategy](#testing-strategy)

---

## System Overview

### 1.1 Purpose

The myAudible system is an AI-powered data pipeline that converts text documents (.md, .pdf, .txt, .docx) into high-quality audio files using the Qwen 3.0 TTS model. The system operates as a systemd-managed service that monitors input directories and processes files asynchronously.

### 1.2 Scope

- **In Scope**: File monitoring, text extraction, semantic chunking, TTS processing, audio stitching, output generation
- **Out of Scope**: Web interface, user authentication, cloud storage integration

### 1.3 Definitions

| Term | Definition |
|------|------------|
| Chunk | A paragraph-sized segment of text sent to the TTS API |
| Sidecar | A JSON metadata file generated alongside the output WAV |
| Path Unit | A systemd unit file that monitors directory changes |
| Inotify | Linux kernel subsystem for file system events |

---

## Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SYSTEMD MANAGER                               │
│  ┌─────────────────────┐    ┌─────────────────────┐                  │
│  │ myaudible-input.path│    │ myaudible.service   │                  │
│  │ (File Monitor)      │───▶│ (Processing Logic)  │                  │
│  └─────────────────────┘    └─────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         myAUDIBLE APPLICATION                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  FileWatcher    │  │  TextProcessor  │  │  ChunkManager       │  │
│  │  (inotify)      │──▶│  (Extractor)    │──▶│  (semchunk)         │  │
│  └─────────────────┘  └─────────────────┘  └──────────┬──────────┘  │
│                                                        │              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────▼──────────┐  │
│  │  OutputManager  │  │  AudioStitcher  │  │  TTSClient          │  │
│  │  (File Ops)     │◀──│  (ffmpeg)       │◀──│  (API Client)       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Qwen 3.0 TTS API: http://192.168.1.104:8008/v1/audio/speech│   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.9+ |
| Async Framework | asyncio | Built-in |
| HTTP Client | aiohttp | 3.9+ |
| PDF Extraction | pdfplumber | 0.11+ |
| DOCX Extraction | python-docx | 1.1+ |
| Semantic Chunking | semchunk | 0.1.0+ |
| Audio Processing | ffmpeg-python | 0.2+ |
| Audio Library | scipy | 1.11+ |
| Configuration | pydantic-settings | 2.1+ |
| Logging | structlog | 23+ |
| Testing | pytest | 7.4+ |

### 2.3 Design Patterns

- **Observer Pattern**: FileWatcher observes directory for changes
- **Factory Pattern**: TextExtractor creates appropriate parser based on file type
- **Strategy Pattern**: ChunkManager uses semchunk strategy for segmentation
- **Retry Pattern**: TTSClient implements exponential backoff
- **Composite Pattern**: AudioStitcher combines multiple WAV files

---

## Component Design

### 3.1 FileWatcher Component

**Responsibility**: Monitor input directory for new files using inotify.

**Class**: `FileWatcher`

**Key Methods**:
- `start()`: Start monitoring the input directory
- `stop()`: Stop monitoring and clean up resources
- `register_callback(callback)`: Register handler for file events

**Implementation Details**:
```python
class FileWatcher:
    def __init__(self, input_path: Path, callback: Callable):
        self.input_path = input_path
        self.callback = callback
        self.watcher = inotifywatch.InotifyWatcher()
        self.watches = {}
    
    async def start(self):
        """Start monitoring the input directory."""
        self.watches[self.input_path] = self.watcher.add_watch(
            str(self.input_path),
            inotifywatch.IN_MODIFY | inotifywatch.IN_CLOSE_WRITE
        )
        await self._process_events()
    
    async def _process_events(self):
        """Process inotify events asynchronously."""
        async for event in self.watcher:
            if event.is_close_write():
                await self.callback(event.path)
```

### 3.2 TextExtractor Component

**Responsibility**: Extract plain text from various document formats.

**Class**: `TextExtractor`

**Supported Formats**:
- `.md` - Markdown files
- `.pdf` - PDF documents
- `.txt` - Plain text files
- `.docx` - Word documents

**Key Methods**:
- `extract(file_path: Path) -> str`: Extract text from file
- `_extract_markdown(file_path: Path) -> str`: Extract from markdown
- `_extract_pdf(file_path: Path) -> str`: Extract from PDF
- `_extract_txt(file_path: Path) -> str`: Extract from text
- `_extract_docx(file_path: Path) -> str`: Extract from Word

**Implementation Details**:
```python
class TextExtractor:
    def __init__(self):
        self.markdown_parser = MarkdownParser()
        self.pdf_parser = PDFParser()
        self.docx_parser = DOCXParser()
    
    async def extract(self, file_path: Path) -> str:
        """Extract text from file based on extension."""
        ext = file_path.suffix.lower()
        
        if ext == '.md':
            return await self._extract_markdown(file_path)
        elif ext == '.pdf':
            return await self._extract_pdf(file_path)
        elif ext == '.txt':
            return await self._extract_txt(file_path)
        elif ext == '.docx':
            return await self._extract_docx(file_path)
        else:
            raise UnsupportedFormatError(f"Unsupported format: {ext}")
    
    async def _extract_markdown(self, file_path: Path) -> str:
        """Extract text from markdown, stripping formatting."""
        content = file_path.read_text(encoding='utf-8')
        # Remove markdown syntax
        content = re.sub(r'#+', '', content)  # Headers
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*([^*]+)\*', r'\1', content)  # Italic
        content = re.sub(r'```[\s\S]*?```', '', content)  # Code blocks
        return content
    
    async def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF preserving reading order."""
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return '\n\n'.join(text_parts)
    
    async def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX preserving paragraph flow."""
        from docx import Document
        
        doc = Document(file_path)
        paragraphs = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        # Extract table text
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text:
                        paragraphs.append(text)
        
        return '\n\n'.join(paragraphs)
```

### 3.3 ChunkManager Component

**Responsibility**: Split extracted text into semantic chunks for TTS processing.

**Class**: `ChunkManager`

**Key Methods**:
- `chunk(text: str) -> List[str]`: Split text into chunks
- `calculate_overlap() -> int`: Calculate overlap size

**Configuration**:
- `MAX_CHUNK_CHARS`: Maximum characters per chunk (default: 500)
- `OVERLAP_RATIO`: Overlap percentage (default: 0.1)

**Implementation Details**:
```python
from semchunk import chunk_by_size

class ChunkManager:
    def __init__(self, max_chars: int = 500, overlap_ratio: float = 0.1):
        self.max_chars = max_chars
        self.overlap_ratio = overlap_ratio
    
    async def chunk(self, text: str) -> List[str]:
        """Split text into semantic chunks using semchunk."""
        # semchunk provides semantic-aware chunking
        chunks = chunk_by_size(
            text=text,
            chunk_size=self.max_chars,
            overlap=int(self.max_chars * self.overlap_ratio)
        )
        return chunks
    
    async def add_silence_markers(self, chunks: List[str]) -> List[Dict]:
        """Add silence markers between paragraph breaks."""
        marked_chunks = []
        for i, chunk in enumerate(chunks):
            marked_chunks.append({
                'index': i,
                'text': chunk,
                'has_silence_before': i > 0,
                'silence_duration_ms': 500 if i > 0 else 0
            })
        return marked_chunks
```

### 3.4 TTSClient Component

**Responsibility**: Interface with Qwen 3.0 TTS API for audio generation.

**Class**: `TTSClient`

**Key Methods**:
- `generate_speech(text: str, voice_config: VoiceConfig) -> bytes`: Generate audio
- `retry_with_backoff(func, max_retries: int)`: Retry failed requests

**Configuration**:
- `TTS_ENDPOINT`: API URL (default: `http://192.168.1.104:8008/v1/audio/speech`)
- `RETRY_ATTEMPTS`: Maximum retry attempts (default: 3)
- `BASE_BACKOFF_MS`: Base backoff time in milliseconds (default: 1000)

**Implementation Details**:
```python
import aiohttp
import asyncio

class TTSClient:
    def __init__(self, endpoint: str, retry_attempts: int = 3):
        self.endpoint = endpoint
        self.retry_attempts = retry_attempts
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def generate_speech(
        self, 
        text: str, 
        voice_config: Optional[VoiceConfig] = None
    ) -> bytes:
        """Generate speech from text with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                payload = {
                    'input': text,
                    'model': 'qwen-3.0-tts',
                    'voice': voice_config.dict() if voice_config else None
                }
                
                async with self.session.post(
                    self.endpoint,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    elif response.status in [429, 500, 502, 503, 504]:
                        await self._handle_retry(attempt, response.status)
                    else:
                        raise TTSAPIError(f"API error: {response.status}")
                        
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise
                await asyncio.sleep(self._calculate_backoff(attempt))
        
        raise TTSAPIError("Max retries exceeded")
    
    async def _handle_retry(self, attempt: int, status: int, retry_after: Optional[int] = None):
        """Handle retryable errors."""
        if status == 429:
            await asyncio.sleep(retry_after or 1)
        else:
            await asyncio.sleep(self._calculate_backoff(attempt))
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        import random
        base = 1000  # 1 second
        exponential = base * (2 ** attempt)
        jitter = random.uniform(0, 0.5) * exponential
        return (exponential + jitter) / 1000
```

### 3.5 AudioStitcher Component

**Responsibility**: Combine WAV chunks into final output using ffmpeg.

**Class**: `AudioStitcher`

**Key Methods**:
- `stitch(chunks: List[AudioChunk], output_path: Path)`: Combine audio files
- `add_silence(silence_path: Path, duration_ms: int)`: Generate silence asset
- `normalize_audio(input_path: Path, output_path: Path)`: Apply normalization

**Implementation Details**:
```python
import subprocess
from pathlib import Path

class AudioStitcher:
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        self.ffmpeg_path = ffmpeg_path
    
    async def stitch(
        self, 
        wav_files: List[Path], 
        output_path: Path,
        add_silence_between: bool = True,
        silence_duration_ms: int = 500
    ):
        """Stitch WAV files using ffmpeg concat demuxer."""
        # Generate silence file if needed
        silence_file = None
        if add_silence_between and len(wav_files) > 1:
            silence_file = await self._generate_silence(silence_duration_ms)
        
        # Create concat list file
        concat_list = Path(output_path.parent / 'concat_list.txt')
        with open(concat_list, 'w') as f:
            for i, wav_file in enumerate(wav_files):
                f.write(f"file '{wav_file.absolute()}'\n")
                if i < len(wav_files) - 1 and add_silence_between:
                    f.write(f"file '{silence_file}'\n")
        
        # Run ffmpeg concat
        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy',
            '-y',
            str(output_path)
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            raise AudioProcessingError(f"FFmpeg error: {stderr.decode()}")
        
        # Cleanup concat list
        concat_list.unlink()
        
        # Apply normalization
        normalized_path = output_path.parent / f"normalized_{output_path.name}"
        await self._normalize_audio(output_path, normalized_path)
        
        # Replace original with normalized
        normalized_path.rename(output_path)
    
    async def _generate_silence(self, duration_ms: int) -> Path:
        """Generate a silence audio file."""
        silence_file = Path(tempfile.gettempdir()) / f"silence_{duration_ms}.wav"
        
        cmd = [
            self.ffmpeg_path,
            '-f', 'lavfi',
            '-i', f'anullsrc=r=44100:cl=mono',
            '-t', str(duration_ms / 1000),
            '-c:a', 'pcm_s16le',
            '-y',
            str(silence_file)
        ]
        
        await asyncio.create_subprocess_exec(*cmd)
        
        return silence_file
    
    async def _normalize_audio(self, input_path: Path, output_path: Path):
        """Apply loudness normalization using ffmpeg."""
        cmd = [
            self.ffmpeg_path,
            '-i', str(input_path),
            '-af', 'loudnorm=I=-16:TP=-2:LRA=11',
            '-y',
            str(output_path)
        ]
        
        await asyncio.create_subprocess_exec(*cmd)
```

### 3.6 OutputManager Component

**Responsibility**: Manage output file generation and metadata.

**Class**: `OutputManager`

**Key Methods**:
- `save_wav(audio_data: bytes, original_name: str) -> Path`: Save WAV file
- `save_sidecar(metadata: dict, output_path: Path)`: Save metadata JSON
- `move_to_processed(file_path: Path)`: Move processed file to archive

**Implementation Details**:
```python
import json
from datetime import datetime

class OutputManager:
    def __init__(self, output_dir: Path, processed_dir: Optional[Path] = None):
        self.output_dir = output_dir
        self.processed_dir = processed_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_wav(
        self, 
        audio_data: bytes, 
        original_name: str,
        timestamp: Optional[datetime] = None
    ) -> Path:
        """Save WAV file with timestamp."""
        ts = timestamp or datetime.now()
        filename = f"{original_name}_{ts.strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = self.output_dir / filename
        
        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(audio_data)
        
        return output_path
    
    async def save_sidecar(
        self, 
        metadata: dict, 
        output_path: Path
    ):
        """Save sidecar JSON metadata file."""
        sidecar_path = output_path.parent / f"{output_path.stem}.json"
        
        sidecar_data = {
            'generated_at': datetime.now().isoformat(),
            'output_file': output_path.name,
            'duration_seconds': metadata.get('duration', 0),
            'word_count': metadata.get('word_count', 0),
            'chunk_count': metadata.get('chunk_count', 0),
            'voice_config': metadata.get('voice_config', {}),
            'source_file': metadata.get('source_file', ''),
            'processing_status': metadata.get('status', 'completed')
        }
        
        async with aiofiles.open(sidecar_path, 'w') as f:
            await f.write(json.dumps(sidecar_data, indent=2))
    
    async def move_to_processed(self, file_path: Path):
        """Move processed file to archive directory."""
        if self.processed_dir:
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            dest = self.processed_dir / file_path.name
            await asyncio.to_thread(file_path.rename, dest)
```

---

## Data Flow

### 4.1 Processing Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Input File │────▶│  Text        │────▶│  Chunk       │
│  (.md/.pdf/  │     │  Extractor   │     │  Manager     │
│   .txt/.docx)│     │              │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Output     │◀────│  Audio       │◀────│  TTS         │
│   WAV +      │     │  Stitcher    │     │  Client      │
│   Sidecar    │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 4.2 State Machine

```
┌─────────────────┐
│   IDLE          │
└──────┬──────────┘
       │ File Detected
       ▼
┌─────────────────┐     ┌─────────────────┐
│   PROCESSING    │────▶│   ERROR         │
│   (Active)      │     │   (Retry/Fail)  │
└──────┬──────────┘     └─────────────────┘
       │
       │ All Chunks Processed
       ▼
┌─────────────────┐     ┌─────────────────┐
│   STITCHING     │────▶│   ERROR         │
│                 │     │                 │
└──────┬──────────┘     └─────────────────┘
       │
       │ Stitch Complete
       ▼
┌─────────────────┐
│   OUTPUT        │
│   (Complete)    │
└─────────────────┘
```

### 4.3 Data Structures

```python
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from datetime import datetime

@dataclass
class ProcessingJob:
    """Represents a file processing job."""
    job_id: str
    source_file: Path
    status: str  # 'pending', 'processing', 'completed', 'failed'
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class AudioChunk:
    """Represents a single audio chunk."""
    chunk_id: str
    text: str
    audio_data: bytes
    duration_ms: int
    sequence_number: int

@dataclass
class ProcessingMetadata:
    """Metadata for processed files."""
    source_file: str
    word_count: int
    chunk_count: int
    total_duration_seconds: float
    voice_config: dict
    processing_time_seconds: float
    status: str
```

---

## API Specifications

### 5.1 Qwen 3.0 TTS API

**Endpoint**: `http://192.168.1.104:8008/v1/audio/speech`

**Request Format**:
```json
{
    "input": "Text to convert to speech",
    "model": "qwen-3.0-tts",
    "voice": {
        "ref_audio": "base64_encoded_audio",
        "ref_text": "optional_reference_text",
        "voice_design": "Deep, raspy male voice"
    }
}
```

**Response Format**:
```json
{
    "audio": "base64_encoded_wav_data",
    "duration_seconds": 5.2,
    "model": "qwen-3.0-tts"
}
```

**Error Responses**:
```json
{
    "error": {
        "code": "RATE_LIMITED",
        "message": "Too many requests",
        "retry_after": 60
    }
}
```

### 5.2 Internal API (Optional Web Interface)

**GET /health**: Health check endpoint
```json
{
    "status": "healthy",
    "uptime_seconds": 3600,
    "jobs_processed": 42,
    "jobs_failed": 1
}
```

**GET /stats**: Processing statistics
```json
{
    "queue_size": 5,
    "processing_rate": "2.5 min/min",
    "last_job_duration": 12.3
}
```

---

## Database Schema

### 6.1 SQLite Schema (for job tracking)

```sql
-- Jobs table for tracking processing state
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    output_file TEXT,
    metadata_json TEXT
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

-- Chunk tracking table
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    text_content TEXT,
    audio_file TEXT,
    duration_ms INTEGER,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_job ON chunks(job_id);
```

### 6.2 In-Memory Cache (for active jobs)

```python
from dataclasses import dataclass
from typing import Dict, Optional
import asyncio

@dataclass
class JobState:
    """In-memory job state for active processing."""
    job_id: str
    chunks_generated: int
    chunks_stitched: bool
    temp_files: List[Path]
    lock: asyncio.Lock

class JobTracker:
    """Track active processing jobs in memory."""
    
    def __init__(self):
        self.jobs: Dict[str, JobState] = {}
        self._lock = asyncio.Lock()
    
    async def create_job(self, job_id: str, source_file: Path) -> JobState:
        async with self._lock:
            state = JobState(
                job_id=job_id,
                chunks_generated=0,
                chunks_stitched=False,
                temp_files=[],
                lock=asyncio.Lock()
            )
            self.jobs[job_id] = state
            return state
    
    async def mark_chunk_complete(self, job_id: str):
        async with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].chunks_generated += 1
    
    async def cleanup(self, job_id: str):
        """Clean up job state and temp files."""
        async with self._lock:
            if job_id in self.jobs:
                state = self.jobs[job_id]
                for temp_file in state.temp_files:
                    if temp_file.exists():
                        temp_file.unlink()
                del self.jobs[job_id]
```

---

## Configuration

### 7.1 Configuration Classes

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List

class TTSConfig(BaseSettings):
    """TTS API configuration."""
    endpoint: str = Field(
        default="http://192.168.1.104:8008/v1/audio/speech",
        description="Qwen 3.0 TTS API endpoint"
    )
    model: str = Field(default="qwen-3.0-tts", description="TTS model name")
    retry_attempts: int = Field(default=3, ge=1, description="Max retry attempts")
    timeout_seconds: int = Field(default=60, ge=1, description="API timeout")

class ProcessingConfig(BaseSettings):
    """Processing pipeline configuration."""
    input_dir: str = Field(default="/input", description="Input directory path")
    output_dir: str = Field(default="/output", description="Output directory path")
    processed_dir: Optional[str] = Field(default="/processed", description="Processed files directory")
    
    chunk_max_chars: int = Field(default=500, ge=1, description="Max chars per chunk")
    chunk_overlap_ratio: float = Field(default=0.1, ge=0, le=1, description="Chunk overlap ratio")
    
    max_parallel_jobs: int = Field(default=2, ge=1, description="Max concurrent jobs")
    
    add_silence_between: bool = Field(default=True, description="Add silence between chunks")
    silence_duration_ms: int = Field(default=500, ge=0, description="Silence duration in ms")

class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json/text)")
    output_file: Optional[str] = Field(default=None, description="Log file path")

class AppConfig(BaseSettings):
    """Main application configuration."""
    tts: TTSConfig = Field(default_factory=TTSConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    class Config:
        env_prefix = "MYAUDIBLE_"
        env_file = ".env"
```

### 7.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MYAUDIBLE_TTS_ENDPOINT` | TTS API URL | `http://192.168.1.104:8008/v1/audio/speech` |
| `MYAUDIBLE_PROCESSING_INPUT_DIR` | Input directory path | `/input` |
| `MYAUDIBLE_PROCESSING_OUTPUT_DIR` | Output directory path | `/output` |
| `MYAUDIBLE_PROCESSING_PROCESSED_DIR` | Processed files directory | `/processed` |
| `MYAUDIBLE_PROCESSING_CHUNK_MAX_CHARS` | Max chars per chunk | `500` |
| `MYAUDIBLE_PROCESSING_CHUNK_OVERLAP_RATIO` | Chunk overlap ratio | `0.1` |
| `MYAUDIBLE_PROCESSING_MAX_PARALLEL_JOBS` | Max concurrent jobs | `2` |
| `MYAUDIBLE_PROCESSING_ADD_SILENCE_BETWEEN` | Add silence between chunks | `true` |
| `MYAUDIBLE_PROCESSING_SILENCE_DURATION_MS` | Silence duration | `500` |
| `MYAUDIBLE_LOGGING_LEVEL` | Log level | `INFO` |
| `MYAUDIBLE_LOGGING_FORMAT` | Log format | `json` |

---

## Error Handling

### 8.1 Custom Exceptions

```python
class MyAudibleError(Exception):
    """Base exception for myAudible errors."""
    pass

class UnsupportedFormatError(MyAudibleError):
    """Raised when file format is not supported."""
    pass

class TextExtractionError(MyAudibleError):
    """Raised when text extraction fails."""
    pass

class TTSAPIError(MyAudibleError):
    """Raised when TTS API call fails."""
    pass

class AudioProcessingError(MyAudibleError):
    """Raised when audio processing fails."""
    pass

class ConfigurationError(MyAudibleError):
    """Raised when configuration is invalid."""
    pass
```

### 8.2 Error Handling Strategy

| Error Type | Strategy |
|------------|----------|
| `UnsupportedFormatError` | Log error, skip file, continue processing |
| `TextExtractionError` | Log error with details, mark job as failed |
| `TTSAPIError` (4xx) | Log error, mark job as failed |
| `TTSAPIError` (5xx) | Retry with exponential backoff (max 3 attempts) |
| `AudioProcessingError` | Log error, cleanup temp files, mark job as failed |
| `DiskSpaceError` | Halt processing, send alert |

### 8.3 Structured Logging

```python
import structlog

# Configure structlog for JSON output
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

# Usage
logger = structlog.get_logger()

logger.info(
    "job_started",
    job_id=job_id,
    source_file=str(source_file),
    file_size=file_size
)

logger.error(
    "job_failed",
    job_id=job_id,
    error=str(e),
    traceback=traceback.format_exc()
)
```

---

## Security

### 9.1 Input Validation

```python
from pathlib import Path
from typing import List

ALLOWED_EXTENSIONS = {'.md', '.pdf', '.txt', '.docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file_path: Path) -> bool:
    """Validate input file for processing."""
    # Check extension
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {file_path.suffix}")
    
    # Check file size
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_path.stat().st_size}")
    
    # Check for path traversal
    if '..' in file_path.parts:
        raise ValueError("Path traversal detected")
    
    return True
```

### 9.2 Input Sanitization

```python
import re

def sanitize_text(text: str) -> str:
    """Sanitize text to prevent injection attacks."""
    # Remove control characters except common whitespace
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Limit text length
    if len(text) > 100000:
        text = text[:100000]
    
    return text
```

### 9.3 File System Security

- Run service as non-root user
- Use dedicated input/output directories with restricted permissions
- Validate all file paths to prevent path traversal
- Clean up temporary files after processing

---

## Deployment

### 10.1 Systemd Configuration

**myaudible-input.path**:
```ini
[Unit]
Description=myAudible Input Directory Monitor
After=network.target

[Path]
PathExists=/input
DirectoryMode=0755
Unit=myaudible.service

[Install]
WantedBy=multi-user.target
```

**myaudble.service**:
```ini
[Unit]
Description=myAudible Processing Service
After=network.target myaudible-input.path
Requires=myaudible-input.path

[Service]
Type=simple
User=myaudible
Group=myaudible
WorkingDirectory=/opt/myaudible
ExecStart=/opt/myaudible/venv/bin/python -m myaudible.app
EnvironmentFile=/opt/myaudible/.env
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

### 10.2 Directory Structure

```
/opt/myaudible/
├── venv/                          # Python virtual environment
├── myaudible/                     # Application package
│   ├── __init__.py
│   ├── app.py                     # Main application entry
│   ├── main.py                    # Async entry point
│   ├── config.py                  # Configuration loading
│   ├── file_watcher.py            # File monitoring
│   ├── text_extractor.py          # Text extraction
│   ├── chunk_manager.py           # Text chunking
│   ├── tts_client.py              # TTS API client
│   ├── audio_stitcher.py          # Audio processing
│   ├── output_manager.py          # Output handling
│   └── exceptions.py              # Custom exceptions
├── input/                         # Input directory (monitored)
├── output/                        # Output directory
├── processed/                     # Archived processed files
├── logs/                          # Application logs
├── temp/                          # Temporary files
├── .env                           # Environment configuration
├── requirements.txt               # Python dependencies
├── setup.py                       # Installation script
└── README.md                      # Documentation
```

### 10.3 Installation Script

```bash
#!/bin/bash
# install.sh

set -e

INSTALL_DIR="/opt/myaudible"
PYTHON_VERSION="3.11"

# Create user
if ! id -u myaudible >/dev/null 2>&1; then
    useradd -r -s /bin/false myaudible
fi

# Create directories
mkdir -p $INSTALL_DIR/{input,output,processed,logs,temp}
chown -R myaudible:myaudible $INSTALL_DIR

# Create virtual environment
cd $INSTALL_DIR
python$PYTHON_VERSION -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Install systemd services
cp myaudible*.path /etc/systemd/system/
cp myaudible.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start
systemctl enable myaudble-input.path
systemctl start myaudible-input.path

echo "myAudible installed successfully!"
```

---

## Testing Strategy

### 11.1 Test Categories

| Category | Description | Tools |
|----------|-------------|-------|
| Unit Tests | Individual component testing | pytest, unittest |
| Integration Tests | Component interaction | pytest-asyncio |
| End-to-End Tests | Full pipeline testing | pytest |
| Performance Tests | Load and stress testing | pytest-benchmark |

### 11.2 Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── test_text_extractor.py
│   ├── test_chunk_manager.py
│   ├── test_tts_client.py
│   └── test_audio_stitcher.py
├── integration/
│   ├── test_processing_pipeline.py
│   └── test_file_watcher.py
├── e2e/
│   └── test_full_pipeline.py
├── fixtures/
│   ├── sample.md
│   ├── sample.pdf
│   ├── sample.txt
│   └── sample.docx
└── mocks/
    └── mock_tts_server.py
```

### 11.3 Example Test Cases

```python
import pytest
from pathlib import Path
import tempfile
import asyncio

class TestTextExtractor:
    @pytest.mark.asyncio
    async def test_extract_markdown(self, sample_md_file):
        """Test markdown text extraction."""
        extractor = TextExtractor()
        text = await extractor.extract(sample_md_file)
        
        assert "Hello World" in text
        assert "#" not in text  # Headers should be stripped
    
    @pytest.mark.asyncio
    async def test_extract_pdf(self, sample_pdf_file):
        """Test PDF text extraction."""
        extractor = TextExtractor()
        text = await extractor.extract(sample_pdf_file)
        
        assert len(text) > 0
        assert isinstance(text, str)
    
    @pytest.mark.asyncio
    async def test_extract_docx(self, sample_docx_file):
        """Test DOCX text extraction."""
        extractor = TextExtractor()
        text = await extractor.extract(sample_docx_file)
        
        assert len(text) > 0
    
    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        """Test unsupported file format handling."""
        extractor = TextExtractor()
        with tempfile.NamedTemporaryFile(suffix='.xyz') as f:
            with pytest.raises(UnsupportedFormatError):
                await extractor.extract(Path(f.name))

class TestChunkManager:
    @pytest.mark.asyncio
    async def test_chunk_text(self):
        """Test text chunking."""
        manager = ChunkManager(max_chars=100)
        text = "This is a test. " * 20
        chunks = await manager.chunk(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100
    
    @pytest.mark.asyncio
    async def test_chunk_overlap(self):
        """Test chunk overlap for smooth transitions."""
        manager = ChunkManager(max_chars=50, overlap_ratio=0.2)
        text = "Hello world. This is a test. " * 10
        chunks = await manager.chunk(text)
        
        # Verify overlap exists between consecutive chunks
        for i in range(len(chunks) - 1):
            overlap = set(chunks[i].split()) & set(chunks[i+1].split())
            assert len(overlap) > 0
```

### 11.4 Test Coverage Goals

- **Unit Tests**: 80%+ coverage
- **Integration Tests**: All critical paths
- **E2E Tests**: Full pipeline scenarios

---

## Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| Inotify | Linux kernel subsystem for file system events |
| Semchunk | Semantic-aware text chunking library |
| Sidecar | Metadata file generated alongside output |
| Path Unit | Systemd unit for directory monitoring |
| Exponential Backoff | Retry strategy with increasing delays |

### B. References

- [Qwen 3.0 TTS API Documentation](http://192.168.1.104:8008/docs)
- [semchunk Library](https://github.com/example/semchunk)
- [pdfplumber Documentation](https://pdfplumber.readthedocs.io/)
- [python-docx Documentation](https://python-docx.readthedocs.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Systemd Path Units](https://www.freedesktop.org/software/systemd/man/systemd.path.html)

### C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-04-19 | Initial | Initial design document |
