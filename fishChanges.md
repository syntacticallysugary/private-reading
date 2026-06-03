# Fish TTS Migration — Change Log & Revert Guide

This document captures every change made when migrating from Qwen TTS to Fish TTS.
To revert, apply the "Before" values in each section.

---

## 1. `private_reading/core/tts_client.py`

### Removed at module level
```python
# REMOVED — was after imports
import os
TTS_SEED: int = int(os.environ.get("TTS_SEED", 42))
from private_reading.models import VoiceConfig

# REMOVED — local TTSConfig stub class (was not the real config)
class TTSConfig:
    endpoint: str = "http://192.168.1.104:8008/v1/audio/speech"
    retry_attempts: int = 3
    timeout_seconds: int = 600
```

### `TTSClient.__init__` — Before → After

**Before:**
```python
def __init__(
    self,
    endpoint: str,
    voice: str = "",
    seed: int = TTS_SEED,
    retry_attempts: int = 3,
    timeout_seconds: int = 600,
):
    self.endpoint = endpoint
    self.voice = voice
    self.seed = seed
    self.retry_attempts = retry_attempts
    self.timeout_seconds = timeout_seconds
    self._session: Optional[object] = None
```

**After:**
```python
def __init__(
    self,
    endpoint: str,
    reference_id: str = "",
    temperature: float = 0.8,
    top_p: float = 0.8,
    repetition_penalty: float = 1.1,
    retry_attempts: int = 3,
    timeout_seconds: int = 600,
):
    self.endpoint = endpoint
    self.reference_id = reference_id
    self.temperature = temperature
    self.top_p = top_p
    self.repetition_penalty = repetition_penalty
    self.retry_attempts = retry_attempts
    self.timeout_seconds = timeout_seconds
    self._session: Optional[object] = None
```

### `generate_speech` signature — Before → After

**Before:**
```python
async def generate_speech(self, text: str, voice_config: Optional[VoiceConfig] = None) -> bytes:
    ...
    return await self._do_generate(text, voice_config=voice_config)
```

**After:**
```python
async def generate_speech(self, text: str) -> bytes:
    ...
    return await self._do_generate(text)
```

### `_do_generate` payload — Before → After

**Before:**
```python
payload: Dict = {
    "input": text,
    "model": "qwen",
    "response_format": "wav",
}
if self.voice:
    payload["voice"] = self.voice
if self.seed is not None:
    payload["seed"] = self.seed
```

**After:**
```python
payload: Dict = {
    "text": text,
    "format": "wav",
    "references": [],
    "streaming": False,
    "temperature": self.temperature,
    "top_p": self.top_p,
    "repetition_penalty": self.repetition_penalty,
}
if self.reference_id:
    payload["reference_id"] = self.reference_id
```

---

## 2. `private_reading/config.py`

### Removed at module level
```python
# REMOVED
import os
TTS_SEED: int = int(os.environ.get("TTS_SEED", 42))
```

### `TTSConfig` class — Before → After

**Before:**
```python
class TTSConfig(BaseSettings):
    """TTS API configuration."""

    endpoint: str = "http://192.168.1.104:8008/v1/audio/speech"
    voice: str = ""
    seed: int = TTS_SEED
    retry_attempts: int = 3
    base_backoff_ms: int = 1000

    class Config:
        env_prefix = "TTS_"
```

**After:**
```python
class TTSConfig(BaseSettings):
    """Fish TTS API configuration."""

    endpoint: str = "http://192.168.1.104:8013/v1/tts"
    reference_id: str = ""
    temperature: float = 0.8
    top_p: float = 0.8
    repetition_penalty: float = 1.1
    retry_attempts: int = 3
    base_backoff_ms: int = 1000

    class Config:
        env_prefix = "TTS_"
```

---

## 3. `private_reading/core/pipeline.py`

### TTSClient instantiation — Before → After

**Before:**
```python
self.tts_client = TTSClient(
    endpoint=config.tts.endpoint,
    voice=config.tts.voice,
    seed=config.tts.seed,
    retry_attempts=config.tts.retry_attempts,
)
```

**After:**
```python
self.tts_client = TTSClient(
    endpoint=config.tts.endpoint,
    reference_id=config.tts.reference_id,
    temperature=config.tts.temperature,
    top_p=config.tts.top_p,
    repetition_penalty=config.tts.repetition_penalty,
    retry_attempts=config.tts.retry_attempts,
)
```

---

## 4. `private_reading/cli.py`

### Argument parser — Before → After

**Before:**
```python
optional.add_argument("--voice", default=None, help="Voice ID for TTS")
```

**After:**
```python
optional.add_argument("--reference-id", default=None, dest="reference_id", help="Pre-registered Fish TTS voice reference ID")
```

### Epilog example — Before → After

**Before:**
```
"  python -m private_reading -i document.md -o ./output -v --voice echo\n"
```

**After:**
```
"  python -m private_reading -i document.md -o ./output -v --reference-id my-voice\n"
```

### `build_config` TTSConfig construction — Before → After

**Before:**
```python
tts=TTSConfig(voice=args.voice) if args.voice else TTSConfig(),
```

**After:**
```python
tts=TTSConfig(reference_id=args.reference_id) if args.reference_id else TTSConfig(),
```

---

## 5. `.env`

### TTS block — Before → After

**Before:**
```
# Endpoint of your Qwen TTS inference server.
TTS_ENDPOINT=http://192.168.1.104:8008/v1/audio/speech
# Natural language voice design prompt (leave blank for server default voice).
# Describe timbre, tone, pacing, emotion — the more specific, the better.
# Example: "A warm, enthusiastic female teacher in her 30s, speaks with a
#           friendly tone, uses natural pauses, and sounds encouraging."
TTS_VOICE=A warm, friendly, intimate and energetic middle aged male narrator.
TTS_SEED=42
```

**After:**
```
# Endpoint of your Fish TTS inference server.
TTS_ENDPOINT=http://192.168.1.104:8013/v1/tts
# Pre-registered voice reference ID (leave blank for server default voice).
# Register a voice via POST /v1/references/add, then paste the returned ID here.
TTS_REFERENCE_ID=
# Generation parameters (Fish TTS defaults)
TTS_TEMPERATURE=0.8
TTS_TOP_P=0.8
TTS_REPETITION_PENALTY=1.1
```

---

## 6. `docs/design.md` — Summary of changes

- Section 1.1: "Qwen 3.0 TTS model" → "Fish TTS server"; "systemd-managed" → "Docker-managed"
- Section 2.1 diagram: endpoint URL changed from `/v1/audio/speech` to `/v1/tts`; label "Qwen 3.0 TTS API" → "Fish TTS API"
- Section 3.4 (TTSClient): description, configuration fields, and example payload fully replaced with Fish API schema
- Section 5.1: Entire API spec replaced — Qwen OpenAI-compat schema → Fish TTS schema; added voice registration instructions
- Section 7.1 (TTSConfig class): fields replaced to match Fish API
- Section 7.2 (env var table): replaced with actual `.env` variable names and Fish defaults
- Appendix B: "Qwen 3.0 TTS API Documentation" → "Fish TTS API Documentation"

---

## 7. `README.md` — Summary of changes

- Tagline: "Qwen TTS server" → "Fish TTS server"
- Prerequisites: "Qwen TTS" → "Fish TTS"
- How It Works step 3: "Qwen server" → "Fish TTS server"
- Configuration / TTS Service table: removed `TTS_VOICE_DESIGN`, `TTS_RETRY_ATTEMPTS`; added `TTS_REFERENCE_ID`, `TTS_TEMPERATURE`, `TTS_TOP_P`, `TTS_REPETITION_PENALTY`, `TTS_RETRY_ATTEMPTS`
- Voice design section replaced with voice reference registration instructions
- Processing table: updated defaults to match current `.env` (chunk size 800, overlap 0.0, semaphore 1)
- CLI Usage: `--voice "..."` → `--reference-id abc123`; flags table updated
- Project structure: tts_client.py description "Qwen TTS" → "Fish TTS"; audio_stitcher note added loudnorm
- Troubleshooting: curl command updated to Fish API schema; added "Voice changes between chunks" entry

---

## Revert Checklist

To fully revert to Qwen TTS:

- [ ] `tts_client.py` — restore `os` import, `TTS_SEED` global, `VoiceConfig` import, `TTSConfig` stub, old `__init__` signature, old `payload` in `_do_generate`
- [ ] `config.py` — restore `import os`, `TTS_SEED = int(os.environ.get(...))`, old `TTSConfig` fields (`voice`, `seed`)
- [ ] `pipeline.py` — restore `voice=config.tts.voice, seed=config.tts.seed` in TTSClient call
- [ ] `cli.py` — restore `--voice` arg and `TTSConfig(voice=args.voice)` construction
- [ ] `.env` — restore `TTS_ENDPOINT=.../v1/audio/speech`, `TTS_VOICE=...`, `TTS_SEED=42`; remove `TTS_REFERENCE_ID`, `TTS_TEMPERATURE`, `TTS_TOP_P`, `TTS_REPETITION_PENALTY`
- [ ] `docs/design.md` and `README.md` — revert doc changes (lower priority)
