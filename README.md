# Private Reading

Convert text documents to audiobooks using a self-hosted TTS server (Fish TTS or Qwen). Drop a file into a watched directory and a WAV file appears in the output directory.

**Supported formats:** Markdown (`.md`), plain text (`.txt`), Word documents (`.docx`), PDF (`.pdf`)

---

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- A running TTS inference server — Fish TTS (e.g. at `http://192.168.1.104:8013`) or Qwen

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
              doc.md.json     (sidecar metadata)
              processed/
                doc.md        (original, archived)
```

The pipeline:
1. **Extract** — pulls plain text from the source file
2. **Chunk** — splits text into TTS-sized segments using semantic chunking
3. **TTS** — sends each chunk to the TTS server (Fish or Qwen), receives WAV audio
4. **Stitch** — ffmpeg concatenates chunks into a single normalized WAV
5. **Archive** — moves the source file to `output/processed/`

---

## Configuration

All configuration lives in `.env`. Copy `.env.example` to get started.

### TTS Service

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_PROVIDER` | `fish` | TTS provider: `fish` or `qwen` |
| `TTS_ENDPOINT` | `http://192.168.1.104:8013/v1/tts` | URL of your TTS server |
| `TTS_REFERENCE_ID` | *(blank — server default)* | Pre-registered voice reference ID (Fish and Qwen base) |
| `TTS_VOICE` | *(blank)* | Natural language voice design prompt (Qwen VoiceDesign only) |
| `TTS_MODEL` | `qwen` | Model name sent in the OpenAI-compatible request (Qwen only) |
| `TTS_TEMPERATURE` | `0.8` | Generation temperature |
| `TTS_TOP_P` | `0.8` | Top-p sampling (Fish only) |
| `TTS_REPETITION_PENALTY` | `1.1` | Repetition penalty (Fish only) |
| `TTS_RETRY_ATTEMPTS` | `3` | Retries on server errors |
| `TTS_BASE_BACKOFF_MS` | `1000` | Base backoff in milliseconds for retry delays |

**Voice consistency — Fish TTS:** Fish TTS uses reference audio for voice cloning. To get a consistent voice across all chunks:

1. Register a reference audio clip with the server:
   ```bash
   curl -X POST http://192.168.1.104:8013/v1/references/add \
     -F "audio=@my-voice-sample.wav"
   # Returns: {"reference_id": "abc123..."}
   ```
2. Set the returned ID in `.env`:
   ```
   TTS_REFERENCE_ID=abc123...
   ```

Leave `TTS_REFERENCE_ID` blank to use the server's built-in default voice.

**Voice consistency — Qwen:** Set `TTS_VOICE` to a natural language description (e.g. `"A calm, clear male voice with a neutral accent"`) to use Qwen's VoiceDesign feature. Alternatively, set `TTS_REFERENCE_ID` to use a pre-registered reference clip. If both are blank the server chooses a default voice.

### Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `PROCESSING_CHUNK_SIZE` | `800` | Max characters per TTS request |
| `PROCESSING_OVERLAP_RATIO` | `0.1` | Overlap between chunks (0.0–1.0) |
| `SEMAPHORE_SIZE` | `10` | Max concurrent TTS requests |

Smaller chunks process faster per request but produce more requests. Larger chunks may time out on slow servers. Reduce `SEMAPHORE_SIZE` if your server struggles under concurrent load.

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
python -m private_reading -i document.md -o ./output

# Watch a directory
python -m private_reading -i ./input -o ./output -w

# With a specific voice reference and verbose logging
python -m private_reading -i document.md -o ./output \
  --reference-id abc123 \
  --verbose
```

All flags:

| Flag | Description |
|------|-------------|
| `-i / --input` | Input file or directory (required) |
| `-o / --output` | Output directory (required) |
| `-w / --watch` | Watch mode — process files as they arrive |
| `-c / --config` | Path to a configuration file |
| `--reference-id` | Pre-registered TTS voice reference ID |
| `--chunk-size` | Override chunk size |
| `--overlap-ratio` | Override overlap ratio |
| `--semaphore-size` | Override max concurrent TTS requests (1–50) |
| `-v / --verbose` | Enable DEBUG logging |

---

## Project Structure

```
private_reading/
├── core/
│   ├── audio_stitcher.py   # ffmpeg-based WAV concatenation + loudnorm
│   ├── chunk_manager.py    # Semantic text chunking
│   ├── file_watcher.py     # inotify-based directory watcher
│   ├── job_tracker.py      # In-memory job state
│   ├── output_manager.py   # WAV + sidecar writing, archiving
│   ├── pipeline.py         # Orchestrates all stages
│   ├── text_extractor.py   # md / txt / docx extraction
│   └── tts_client.py       # Fish / Qwen TTS HTTP client
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
- Check `docker compose logs` for a `pipeline.stage_complete` event for the `extract_text` stage. If absent, the file watcher didn't pick it up — try removing and re-adding the file.
- Verify the file extension is `.md`, `.txt`, `.docx`, or `.pdf`.

**Processing fails mid-way**
- The source file stays in `input/` on failure (not moved to processed).
- Check logs for `pipeline.process_failed` — the `error` field and traceback will indicate which stage failed.
- Re-drop the file to retry.

**TTS requests time out**
- Reduce `PROCESSING_CHUNK_SIZE` so each request covers less text.
- Check that your TTS server is reachable from inside the container: `docker compose exec private-reading python3 -c "import urllib.request; urllib.request.urlopen('http://192.168.1.104:8013/')"`

**Output WAV has no sound or is gibberish**
- Confirm the TTS server is responding correctly:
  ```bash
  curl -s http://192.168.1.104:8013/v1/tts \
    -X POST -H "Content-Type: application/json" \
    -d '{"text":"The quick brown fox.","format":"wav","references":[],"streaming":false}' \
    -o test.wav && file test.wav
  ```
- Play `test.wav` directly to confirm the server is producing audio before debugging the pipeline.

**Voice changes between chunks**
- Set `TTS_REFERENCE_ID` to a pre-registered voice reference, or `TTS_VOICE` (Qwen VoiceDesign) to a fixed description. Without either, the server may randomize voice characteristics per request.
