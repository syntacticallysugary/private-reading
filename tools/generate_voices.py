"""Generate 12 audition voice samples via Qwen3-TTS-VoiceDesign."""

import asyncio
from pathlib import Path

import aiohttp

ENDPOINT = "http://localhost:8008/v1/audio/speech"
OUTPUT_DIR = Path(__file__).parent / "voice_samples"
SAMPLE_TEXT = (
    "Cost optimization is not about choosing the cheapest option"
    " but about aligning cost with usage. "
    "One approach is to use serverless services like Lambda,"
    " which charge only for execution time. "
    "This eliminates idle resource costs. "
    "For predictable workloads, Reserved Instances or Savings Plans"
    " can significantly reduce EC2 costs. "
    "For flexible or fault-tolerant workloads,"
    " Spot Instances provide substantial savings."
)

_RELAXED = (
    "low-key and relaxed, unhurried and easy to listen to, with a natural conversational tone"
)
_INTIMATE = "intimate and empathetic, warm and personal, as if speaking directly to the listener"
_CALM = "calm and grounded, steady and reassuring, clear and composed"
_ENERGETIC = "energetic and engaging, dynamic and expressive, keeping the listener's attention"
_ENTHUSIASTIC = "enthusiastic and friendly, upbeat and warm, genuinely excited about the content"

VOICES = [
    ("m-relaxed", f"A man with a {_RELAXED} voice"),
    ("f-relaxed", f"A woman with a {_RELAXED} voice"),
    ("m-intimate", f"A man with an {_INTIMATE} voice"),
    ("f-intimate", f"A woman with an {_INTIMATE} voice"),
    ("m-calm", f"A man with a {_CALM} voice"),
    ("f-calm", f"A woman with a {_CALM} voice"),
    ("m-energetic", f"A man with an {_ENERGETIC} voice"),
    ("f-energetic", f"A woman with an {_ENERGETIC} voice"),
    ("m-enthusiastic", f"A man with an {_ENTHUSIASTIC} voice"),
    ("f-enthusiastic", f"A woman with an {_ENTHUSIASTIC} voice"),
]


async def generate(session: aiohttp.ClientSession, voice_id: str, description: str) -> None:
    out_path = OUTPUT_DIR / f"{voice_id}.wav"
    print(f"  Generating {voice_id}...")
    async with session.post(
        ENDPOINT,
        json={
            "input": SAMPLE_TEXT,
            "voice": description,
            "response_format": "wav",
            "temperature": 0.7,
        },
        timeout=aiohttp.ClientTimeout(total=120),
    ) as resp:
        resp.raise_for_status()
        out_path.write_bytes(await resp.read())
    print(f"  Saved → {out_path.name}")


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        for voice_id, description in VOICES:
            try:
                await generate(session, voice_id, description)
            except Exception as exc:
                print(f"  ERROR {voice_id}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
