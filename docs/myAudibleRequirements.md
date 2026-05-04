# myAudible - Requirements Document 

## Overview

This document outlines the requirements for an AI data pipeline that processes text files (.md, .pdf, .txt, .docx) through a Text-to-Speech (TTS) model and generates WAV audio output files.

## Functional Requirements

### FR-1: Input File Handling

The system shall support the following input file formats:

Markdown (.md): Strip or render markdown syntax before TTS.

PDF (.pdf): Extract text via structural parsing (prioritizing reading order).

Word (.docx): Extract text using python-docx, targeting paragraph and table objects.

Text (.txt): Standard UTF-8 plain text.

### FR-2: File Monitoring & Orchestration

The system shall:

Actively monitor a designated input directory for new files using inotify.

Trigger processing via systemd path units (.path) and associated services (.service).

Ensure atomicity: Handle CLOSE_WRITE events to ensure files are fully written before processing.

Support a "Processed" or "Archive" directory to move files out of the input queue after completion.

### FR-3: Text Extraction & Normalization

The system shall:

Extract plain text while filtering out non-speakable elements (e.g., raw URLs or terminal escape codes).

Handle encoding: Default to UTF-8; detect and convert common legacy encodings.

DOCX Specifics: Iterate through doc.paragraphs to preserve the natural narrative flow of the document.

### FR-4: Semantic Text Chunking (via semchunk)

The system shall:

Implement semchunk for intelligent text segmentation.

Hierarchy: Prioritize splits at paragraph breaks, then sentence boundaries, ensuring no chunk exceeds MAX_CHUNK_CHARS.

Character Limit: Adhere to a 500-character limit per chunk to prevent TTS timeout or memory errors.

Overlap: Configure a 10% overlap ratio within the semchunk counter to improve prosodic transitions between audio segments.

### FR-5: TTS Processing & Voice Customization

The system shall interface with the Qwen 3.0 TTS endpoint and support:

Voice Cloning: Accept a ref_audio file and optional ref_text transcript to clone specific speakers.

Voice Design: Accept instructions for natural language voice modeling (e.g., "Deep, raspy male voice").

Retries: Implement exponential backoff for HTTP 5xx or 429 errors.

### FR-6: Audio Processing & Stitching (via ffmpeg)

The system shall:

Use ffmpeg to concatenate WAV files.

Normalization: Apply peak normalization via ffmpeg filters (loudnorm or peak).

Silence Injection: Insert 500ms of silence between paragraph-break chunks using a pre-generated silence asset.

###  FR-7: Output Management

The system shall:

Name output files: {original_name}_{timestamp}.wav.

Generate a sidecar JSON metadata file containing original path, duration, word count, and voice parameters used.

Non-Functional Requirements

### NFR-1: Performance

Throughput: Process at least 2 minutes of audio for every 1 minute of real-time processing.

Concurrency: Support up to MAX_PARALLEL files simultaneously.

### NFR-2: Reliability

Persistence: Identify partially processed files on restart using a chunk-tracking manifest.

Logging: Use structured JSON logging for journald compatibility.

Technical Requirements

### TR-1: System Dependencies

Python 3.9+

semchunk: Primary semantic splitting library.

python-docx: Primary Word document extraction library.

pdfplumber: For PDF extraction.

ffmpeg-python: For audio concatenation (requires system ffmpeg).

aiohttp: For asynchronous API calls.

systemd: For service management and path monitoring.

### TR-2: API Integration

- RESTful API client for Qwen 3.0 TTS endpoint
- Proper error handling for API responses
- Support for streaming or batch audio generation

### TR-3: File System Integration

- Systemd path unit for directory monitoring
- Inotify-based file system events (Linux)
- Proper file locking to prevent concurrent processing

### TR-4: Configuration

- Environment-based configuration (environment variables)
- Configuration file support (YAML/JSON)
- Command-line argument support

## System Architecture

```
┌─────────────────┐
│  Input Directory│
│  (.md, .pdf, .txt)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│  Systemd Path   │      │  File Monitor   │
│  Unit Trigger   │─────▶│  (inotify)      │
└────────┬────────┘      └────────┬────────┘
         │                         │
         ▼                         ▼
┌─────────────────────────────────────────┐
│           Processing Pipeline           │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │  Text    │  │  Chunk   │  │  TTS   ││
│  │ Extract  │─▶│  Split   │─▶│  API   ││
│  └──────────┘  └──────────┘  └───┬────┘│
│                                 │       │
│  ┌──────────┐  ┌──────────┐  ┌──▼────┐ │
│  │  Output  │◀─│  Stitch  │◀─│  WAV   │ │
│  │  WAV     │  │  Chunks  │  │  Files │ │
│  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Output Directory│
│  (.wav files)    │
└─────────────────┘
```

## Processing Workflow

1. **File Detection**: Systemd path unit detects new file in input directory
2. **File Validation**: Verify file type and accessibility
3. **Text Extraction**: Extract text content based on file format
4. **Chunking**: Split text into paragraph-sized units
5. **TTS Processing**: Send each chunk to Qwen 3.0 TTS API
6. **Audio Generation**: Receive and store WAV chunks
7. **Stitching**: Combine all chunks into final WAV file
8. **Output**: Save final WAV to output directory
9. **Cleanup**: Optionally move or archive processed input file

## Error Handling

- Invalid file types: Log error and skip
- API failures: Retry with exponential backoff (max 3 attempts)
- Processing errors: Log detailed error and continue with next file
- Disk space issues: Alert and halt processing if critical

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `INPUT_DIR` | Path to input directory | `/input` |
| `OUTPUT_DIR` | Path to output directory | `/output` |
| `TTS_ENDPOINT` | Qwen 3.0 TTS API URL | `http://192.168.1.104:8008/v1/audio/speech` |
| `CHUNK_SIZE` | Maximum characters per chunk | 500 |
| `MAX_PARALLEL` | Maximum concurrent processing | 2 |
| `RETRY_ATTEMPTS` | Number of retry attempts | 3 |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## Future Enhancements

- Support for additional input formats (DOCX, RTF)
- Voice selection and customization
- Audio format options (MP3, OGG)
- Webhook notifications on completion
- Processing queue management
- Progress tracking and reporting

## Version History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1.0 | 2026-04-19 | Initial | Initial requirements document |
