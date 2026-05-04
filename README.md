# myAudible

Convert text documents to audiobooks using a self-hosted Qwen TTS server. Drop a file into a watched directory and a WAV file appears in the output directory.

**Supported formats:** Markdown (`.md`), plain text (`.txt`), Word documents (`.docx`)

---

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- A running Qwen TTS inference server (e.g. at `http://192.168.1.104:8008`)

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set your TTS server endpoint (see [Configuration](#configuration) below).

### 3. Start

```bash
docker compose up -d
```

The container starts immediately and watches for new files.

### 4. Use

```bash
cp my-document.md input/
```

The WAV file appears in `output/` when processing is complete. For a 400-word document, expect 2–5 minutes depending on your TTS server.

### 5. Monitor

```bash
docker compose logs -f
```

Logs are structured JSON. Each processing stage emits an event:
```json
{"stage": "generate_tts", "file": "/input/doc.md", "chunk_count": 8, "event": "pipeline.stage_complete"}
{"file": "/input/doc.md", "success": true, "duration": 142.3, "event": "pipeline.process_complete"}
```

---

## How It Works

```
input/             output/
  doc.md    →   doc.md.wav    (final audio)
              doc.md.json.wav (sidecar metadata)
              processed/
                doc.md        (original, archived)
```

The pipeline:
1. **Extract** — pulls plain text from the source file
2. **Chunk** — splits text into TTS-sized segments using semantic chunking
3. **TTS** — sends each chunk to the Qwen server, receives WAV audio
4. **Stitch** — ffmpeg concatenates chunks into a single WAV
5. **Archive** — moves the source file to `output/processed/`

---

## Configuration

All configuration lives in `.env`. Copy `.env.example` to get started.

### TTS Service

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_ENDPOINT` | `http://192.168.1.104:8008/v1/audio/speech` | URL of your Qwen TTS server |
| `TTS_VOICE_DESIGN` | *(blank — server default)* | Natural language voice prompt |
| `TTS_RETRY_ATTEMPTS` | `3` | Retries on server errors |

**Voice design** is a natural language description of the voice you want. Qwen TTS uses this as a generation prompt — the more specific, the better:

```
# Minimal
TTS_VOICE_DESIGN=A clear male voice.

# Detailed (produces more lifelike results)
TTS_VOICE_DESIGN=A warm, calm male narrator in his 40s. Speaks deliberately with natural pauses between sentences, as if reading aloud from a book.
```

You can describe timbre, pace, emotion, and even environment. Leave it blank to use the server's default voice.

### Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `PROCESSING_CHUNK_SIZE` | `500` | Max characters per TTS request |
| `PROCESSING_OVERLAP_RATIO` | `0.1` | Overlap between chunks (0.0–1.0) |

Smaller chunks process faster per request but produce more requests. Larger chunks may time out on slow servers.

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_FORMAT` | `json` | `json` (structured) or `text` (human-readable) |

---

## Docker Commands

```bash
# Start (stays up across reboots)
docker compose up -d

# Stop without removing
docker compose stop

# Remove container (input/output directories are preserved)
docker compose down

# Rebuild after config or code changes
docker compose build && docker compose down && docker compose up -d

# Follow logs
docker compose logs -f

# Check status
docker compose ps
```

---

## CLI Usage (without Docker)

If you prefer to run directly:

```bash
pip install -r requirements.txt
pip install -e .

# Process a single file
python -m myaudible -i document.md -o ./output

# Watch a directory
python -m myaudible -i ./input -o ./output -w

# With voice design and verbose logging
python -m myaudible -i document.md -o ./output \
  --voice "A calm, measured female narrator" \
  --verbose
```

All flags:

| Flag | Description |
|------|-------------|
| `-i / --input` | Input file or directory (required) |
| `-o / --output` | Output directory (required) |
| `-w / --watch` | Watch mode — process files as they arrive |
| `--voice` | Voice design prompt |
| `--chunk-size` | Override chunk size |
| `--overlap-ratio` | Override overlap ratio |
| `-v / --verbose` | Enable DEBUG logging |

---

## Project Structure

```
myaudible/
├── core/
│   ├── audio_stitcher.py   # ffmpeg-based WAV concatenation
│   ├── chunk_manager.py    # Semantic text chunking
│   ├── file_watcher.py     # inotify-based directory watcher
│   ├── job_tracker.py      # In-memory job state
│   ├── output_manager.py   # WAV + sidecar writing, archiving
│   ├── pipeline.py         # Orchestrates all stages
│   ├── text_extractor.py   # md / txt / docx extraction
│   └── tts_client.py       # Qwen TTS HTTP client
├── cli.py                  # Argument parsing and entry point
├── app.py                  # Application lifecycle
└── config.py               # Pydantic settings classes

input/                      # Drop files here (bind-mounted in Docker)
output/                     # WAV files appear here (bind-mounted in Docker)
Dockerfile
docker-compose.yml
.env.example
```

---

## Troubleshooting

**File dropped but nothing happens**
- Check `docker compose logs` for a `job.created` event. If absent, inotify didn't fire — try removing and re-adding the file.
- Verify the file extension is `.md`, `.txt`, or `.docx`.

**Processing fails mid-way**
- The source file stays in `input/` on failure (not moved to processed).
- Check logs for `pipeline.process_failed` — the `error` field and traceback will indicate which stage failed.
- Re-drop the file to retry.

**TTS requests time out**
- Reduce `PROCESSING_CHUNK_SIZE` so each request covers less text.
- Check that your TTS server is reachable from inside the container: `docker compose exec myaudible python3 -c "import urllib.request; urllib.request.urlopen('http://192.168.1.104:8008/')`

**Output WAV has no sound**
- Confirm the TTS server is responding: `curl -s http://192.168.1.104:8008/v1/audio/speech -X POST -H "Content-Type: application/json" -d '{"input":"test","model":"qwen","response_format":"wav"}' -o test.wav && file test.wav`
