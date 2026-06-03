# Qwen3-TTS Base — Research + Container Analysis

**Date:** 2026-06-02  
**Model:** Qwen3-TTS-12Hz-1.7B-Base  
**Container dir:** `/home/jumbob/Dev/Qwen35/qwen30TTS-base`  
**Paper:** arXiv:2601.15621  
**GitHub:** https://github.com/QwenLM/Qwen3-TTS  
**faster-qwen3-tts:** https://github.com/andimarafioti/faster-qwen3-tts

---

## Model Family Overview

### What's Released (12Hz tokenizer — main open-source branch)

| Model | Params | Streaming | Instruction Control | Primary Use |
|---|---|---|---|---|
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | 1.7B | ✅ | ✅ | Create voices from NL descriptions |
| Qwen3-TTS-12Hz-1.7B-CustomVoice | 1.7B | ✅ | ✅ | 9 preset voices + style instructions |
| Qwen3-TTS-12Hz-1.7B-Base | 1.7B | ✅ | — | 3-sec voice clone; fine-tuning base |
| Qwen3-TTS-12Hz-0.6B-CustomVoice | 0.6B | ✅ | — | 9 preset voices, efficient |
| Qwen3-TTS-12Hz-0.6B-Base | 0.6B | ✅ | — | 3-sec voice clone; fine-tuning base |

### Also in Technical Report (25Hz tokenizer — not yet open-sourced)
- Qwen3-TTS-25Hz-1.7B-Base (better long-form WER, worse speaker similarity than 12Hz)
- Qwen3-TTS-25Hz-1.7B-VoiceEditing, CustomVoice, 0.6B variants

### 9 Preset Speakers (CustomVoice models only — Base has none)
| Speaker | Description | Native Language |
|---|---|---|
| Vivian (十三) | Bright, slightly edgy young female | Chinese |
| Serena (苏瑶) | Warm, gentle young female | Chinese |
| Uncle Fu (福伯) | Seasoned male, low/mellow | Chinese |
| Dylan (晓东) | Youthful Beijing male | Chinese (Beijing dialect) |
| Eric (程川) | Lively Chengdu male, husky brightness | Chinese (Sichuan dialect) |
| Ryan (甜茶) | Dynamic male, strong rhythmic drive | English |
| Aiden (艾登) | Sunny American male, clear midrange | English |
| Ono_Anna (小野杏) | Playful Japanese female, light/nimble | Japanese |
| Sohee (素熙) | Warm Korean female, rich emotion | Korean |

---

## Architecture Deep Dive

### Qwen-TTS-Tokenizer-12Hz (open-sourced, what we use)
- 12.5 Hz, 16 RVQ layers (1 semantic + 15 acoustic), codebook size 2048 each
- Semantic stream: WavLM teacher for first codebook
- Decoder: lightweight fully-causal ConvNet (no DiT/diffusion stack)
- GAN training; multi-scale mel-spectrogram reconstruction loss
- SOTA tokenizer metrics: PESQ-WB 3.21, PESQ-NB 3.68, STOI 0.96, UTMOS 4.16, SIM 0.95

### Qwen-TTS-Tokenizer-25Hz (not open-sourced)
- Single-codebook, built on Qwen2-Audio encoder
- Needs block-wise DiT (Diffusion Transformer) + Flow Matching + BigVGAN vocoder decoder
- Better long-form WER, worse speaker similarity, higher latency than 12Hz

### LM Architecture (confirmed via config.json)
- Architecture: `Qwen3TTSForConditionalGeneration`
- Backbone (Talker): 28 hidden layers, hidden_size 2048, 16 attention heads, 8 KV heads
- max_position_embeddings: 32768, RoPE theta 1000000, MRoPE sections [24, 20, 20]
- Code Predictor: 5 hidden layers, hidden_size 1024, 16 attention heads, 8 KV heads, vocab_size 2048
- Speaker encoder: enc_dim 2048, sample_rate 24000, jointly trained with backbone
- Base model: `spk_id` and `spk_is_dialect` are empty dicts — no preset speakers, voice identity from ref audio only
- transformers_version: 4.57.3

### Dual-Track Streaming
- Per text token → backbone predicts zeroth codebook via linear head
- MTP (Multi-Token Prediction) module predicts all 15 residual codebooks from backbone output
- First audio packet: 101ms (1.7B), 97ms (0.6B)
- Simultaneous streaming text input + streaming audio output

### Speech Tokenizer Config (speech_tokenizer/config.json)
- 12.5Hz, 16 quantizers, codebook_size 2048, input/output sample_rate 24000
- `use_streaming: false` — encoder is non-streaming; streaming happens at LM decode level
- Decoder: 8 attention layers, sliding_window 72, upsample_rates [8, 5, 4, 3]

### Voice Cloning Modes
- **ICL (default):** Full reference audio placed in LM context; requires ref_text transcript; higher quality; longer prefill
- **x-vector only:** Speaker embedding only; no ref_text needed; shorter prefill; cleaner cross-lingual switching; lower quality

### Generation Config Defaults (generation_config.json)
- do_sample: true, temperature: 0.9, top_p: 1.0, top_k: 50, repetition_penalty: 1.05
- max_new_tokens: 8192 (~655 seconds max audio ceiling)
- Both main talker and subtalker use same sampling params

### Training Pipeline
**Pre-training (3 stages):**
1. S1 General: >5M hours multilingual speech, monotonic text→speech
2. S2 High-Quality: quality-stratified CPT to reduce hallucinations
3. S3 Long-Context: max tokens 8192→32768, upsampled long speech

**Post-training (3 stages):**
1. DPO (Direct Preference Optimization): preference pairs from human feedback
2. GSPO + rule-based rewards: capability/stability
3. Lightweight speaker fine-tuning on base model

---

## Performance Benchmarks

### Seed-TTS (Zero-shot voice clone, WER ↓)
| Model | ZH | EN |
|---|---|---|
| Qwen3-TTS-12Hz-1.7B-Base | 0.77 | **1.24** (SOTA open-source) |
| Qwen3-TTS-12Hz-0.6B-Base | 0.92 | 1.32 |
| CosyVoice 3 | **0.71** | 1.45 |
| MiniMax-Speech | 0.83 | 1.65 |

### Tokenizer Comparison (LibriSpeech test-clean)
| Model | NQ | FPS | PESQ-WB | STOI | UTMOS | SIM |
|---|---|---|---|---|---|---|
| Qwen-TTS-Tokenizer-12Hz | 16 | 12.5 | **3.21** | **0.96** | **4.16** | **0.95** |
| Mimi | 16 | 12.5 | 2.88 | 0.94 | 3.87 | 0.87 |
| FireredTTS 2 | 16 | 12.5 | 2.73 | 0.94 | 3.88 | 0.87 |

### InstructTTSEval (Controllability, APS ↑)
- Qwen3TTS-12Hz-1.7B-VoiceDesign: ZH 85.2 / EN 82.9 (SOTA open-source, beats GPT-4o-mini-tts)

### DGX Spark GB10 — faster-qwen3-tts CUDA Graphs (1.7B)
| Mode | RTF | TTFA |
|---|---|---|
| Baseline (no CUDA graphs) | 1.01 | 661ms |
| CUDA graphs (faster-qwen3-tts) | 1.87 | 400ms |

RTF > 1 means faster than real-time. ~85% throughput improvement; ~39% latency reduction.

### RTF by GPU — official qwen-tts with FlashAttention 2
| GPU | VRAM | 0.6B RTF | 1.7B RTF |
|---|---|---|---|
| RTX 4090 | 24GB | 0.38-0.45 | 0.65-0.85 |
| RTX 5090 | 32GB | 0.32-0.38 | 0.48-0.55 |
| A100 40GB | 40GB | 0.28-0.35 | 0.45-0.58 |
| H100 80GB | 80GB | 0.22-0.28 | 0.35-0.48 |

Note: faster-qwen3-tts uses CUDA graphs instead of FlashAttention. These RTF numbers are for official qwen-tts only.

### VRAM Requirements
| Model | Min VRAM | Recommended |
|---|---|---|
| 0.6B | 3 GB | 4 GB |
| 1.7B | 5 GB | 6 GB |

### Long-Form 0.6B Degradation
In real benchmarks: 0.6B Base produced 106 silence gaps >1.5s (some 18-27s) over the same long text that produced only 2 gaps with 1.7B Base. **Do not use 0.6B Base for long-form voice cloning.**

---

## Container Stack

```
vllm/vllm-openai:cu130-nightly  (CUDA 13.0, ARM64/GB10)
  └── faster-qwen3-tts[demo]     (MIT, andimarafioti — CUDA graph acceleration)
        └── server.py            (FastAPI/uvicorn, OpenAI-compatible /v1/audio/speech)
```

### Why This Stack

**Problem:** Official `qwen-tts` depends on `torchaudio`. On DGX Spark (GB10 / Grace Blackwell / ARM64, CUDA 13.0, SM 12.1):
- `pip install torchaudio` fetches x86 or CPU-only wheels
- Build-from-source fails: `torch/csrc/stable/device.h` header mismatches with CUDA 13.0
- NVIDIA pytorch NGC containers don't include torchaudio (deprecated)

**Solution:** `faster-qwen3-tts` has zero torchaudio dependency. Uses `librosa` + `soundfile` for audio I/O. The `vllm/vllm-openai:cu130-nightly` base provides the correct CUDA 13/ARM64 PyTorch environment.

### faster-qwen3-tts Details
- Author: andimarafioti, MIT license, v0.2.6
- Uses `torch.cuda.CUDAGraph` capture on both Talker (28-layer) and Code Predictor (5-layer)
- Single graph replay per decode step instead of ~500 Python→CUDA kernel launches
- Explicitly does NOT use FlashAttention, vLLM, or Triton
- Static KV cache required by CUDA graphs → one request at a time (by design)
- First request triggers graph capture/warmup (slow); subsequent requests replay (fast)
- Benchmarked on DGX Spark GB10 in the project BLOG.md

### Files on Disk
| File | Size | Notes |
|---|---|---|
| models/Qwen3-TTS-Base/model.safetensors | 3.6 GB | 1.7B LM weights, bfloat16 |
| models/Qwen3-TTS-Base/speech_tokenizer/model.safetensors | 651 MB | Tokenizer codec weights |

### Voices
| File | Transcript | Status |
|---|---|---|
| voices/681LeonardLn4.wav | 681LeonardLn4.txt | ✅ Working |
| voices/Domain3short.wav | Domain3short.txt | ✅ Working |
| voices/681 Leonard Ln 4.wav | — | ⚠️ Space in filename; no transcript |

The file with a space in the name is a duplicate of 681LeonardLn4 — different path, same voice, no transcript. Won't fail but is confusing.

### API Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | Returns `{"status": "ok"}` |
| POST | /v1/audio/speech | OpenAI-compatible TTS; streams WAV or PCM |
| POST | /v1/references/add | Upload new voice reference WAV + optional transcript |

Port mapping: 8014 (host) → 8000 (container).

---

## Issues Flagged

### Functional Bug — Fix This
**1. `/v1/references/add` saves uploaded audio as `.wav` regardless of actual format.**  
The endpoint does `VOICES_DIR / f"{ref_id}.wav"` and writes raw bytes from the upload. An MP3 or FLAC upload gets stored with a `.wav` extension but wrong headers. `generate_voice_clone_streaming()` will then receive a malformed file. sox is already installed in the container — conversion or format validation is the fix.

### Behavioral — Know About These
**2. Global `threading.Lock()` serializes all inference.**  
One request at a time, hard-blocked. Required by CUDA graphs' static KV cache. Concurrent clients queue. Expected behavior, not a bug.

**3. CUDA graph warmup on first request.**  
First real request after container start is slow while graphs are captured. The 180s healthcheck start-period covers it, but clients that reconnect after a restart should expect a slow first response.

**4. Temperature mismatch between server default and generation_config.**  
`TTSRequest` defaults to `temperature=0.7`; `generation_config.json` specifies 0.9. Request-level wins when provided. If a client omits temperature, 0.7 applies — not the model's intended 0.9. Intentional or oversight — worth being explicit about.

**5. Duplicate `transcript_path` assignment in server.py.**  
Lines 82 and 90 both set `transcript_path` to the same value. Harmless but dead code.

### Non-Issues (by design)
**6. `[demo]` extra pulls in Gradio.**  
Only affects image size and build time. Can be dropped to `faster-qwen3-tts` in Dockerfile if unused.

**7. No authentication.**  
Open endpoints. Fine for local inference; don't expose port 8014 externally without a proxy.

**8. Heavyweight base image.**  
`vllm-openai` includes Ray, vLLM serving stack — none of which server.py uses. Justified by CUDA 13/ARM64 compatibility. Long-term: pytorch.org ARM64/CUDA 13 builds may enable a leaner base.

---

## Fine-Tuning (Base models — single-speaker SFT)

Only 1.7B-Base and 0.6B-Base support SFT. Multi-speaker FT not yet released.

### Data Format (JSONL)
```json
{"audio":"./data/utt0001.wav","text":"Transcript text.","ref_audio":"./data/ref.wav"}
```
Use the SAME `ref_audio` across all samples for best speaker consistency.

### Pipeline
```bash
cd Qwen3-TTS/finetuning

# Step 1: Extract audio codes
python prepare_data.py \
  --device cuda:0 \
  --tokenizer_model_path Qwen/Qwen3-TTS-Tokenizer-12Hz \
  --input_jsonl train_raw.jsonl \
  --output_jsonl train_with_codes.jsonl

# Step 2: Train
python sft_12hz.py \
  --init_model_path Qwen/Qwen3-TTS-12Hz-1.7B-Base \
  --output_model_path output \
  --train_jsonl train_with_codes.jsonl \
  --batch_size 2 \
  --lr 2e-5 \
  --num_epochs 3 \
  --speaker_name my_speaker
```

### Inference after FT
```python
tts = Qwen3TTSModel.from_pretrained("output/checkpoint-epoch-2", ...)
wavs, sr = tts.generate_custom_voice(text="...", speaker="my_speaker")
```

---

## Long-Form TTS Best Practices

1. **Chunk text:** paragraph-aware splitting, keep sentences <200 chars
2. **Use 1.7B Base**, not 0.6B Base for voice cloning (0.6B degrades badly on long content)
3. **Fixed seed** (e.g., 42) before each chunk to prevent voice drift across chunks
4. **Temperature tuning:** flat output → raise to 0.8-0.9; unstable/garbled → lower to 0.5-0.6
5. **Post-process:** 24kHz PCM mono output; use ffmpeg peak normalize (NOT loudnorm for TTS)
6. **Pacing:** ~157-170 WPM with default 1.7B Base clone

---

## Key Competitive Position

- Beats MiniMax + ElevenLabs on voice clone multilingual (10 langs), WER and speaker similarity
- Beats CosyVoice3 on cross-lingual voice clone (most lang pairs)
- Beats GPT-4o-mini-tts on instruction following (CustomVoice)
- Best open-source VoiceDesign model (beats Mimo-Audio-7B, VoiceSculptor, Parler-TTS)

**Why:** No LM+DiT cascade errors. Pure discrete multi-codebook autoregressive LM + lightweight causal ConvNet decoder = better ceiling, faster, lower latency.

---

## Why Base (not CustomVoice or VoiceDesign)

Base is the ICL (in-context learning) foundation. CustomVoice and VoiceDesign are SFT variants of Base with speaker-specific and instruction data layered on. Base is the right starting point for:
- Zero-shot voice cloning from a reference clip
- Fine-tuning to permanently bake in a specific voice at low data cost
- Evaluating raw model capability before instruction tuning layers are applied
