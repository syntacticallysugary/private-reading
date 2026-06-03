"""Generate 12 audition voice samples via Qwen3-TTS-VoiceDesign."""

import asyncio
import aiohttp
from pathlib import Path

ENDPOINT = "http://192.168.1.104:8008/v1/audio/speech"
OUTPUT_DIR = Path("/home/jimbob/Dev/myaudible/tools/voice_samples")
SAMPLE_TEXT = (
    "Cost optimization is not about choosing the cheapest option but about aligning cost with usage. "
    "One approach is to use serverless services like Lambda, which charge only for execution time. "
    "This eliminates idle resource costs. "
    "For predictable workloads, Reserved Instances or Savings Plans can significantly reduce EC2 costs. "
    "For flexible or fault-tolerant workloads, Spot Instances provide substantial savings."
)

VOICES = [
    ("m-relaxed",     "A man with a low-key and relaxed voice, unhurried and easy to listen to, with a natural conversational tone"),
    ("f-relaxed",     "A woman with a low-key and relaxed voice, unhurried and easy to listen to, with a natural conversational tone"),
    ("m-intimate",    "A man with an intimate and empathetic voice, warm and personal, as if speaking directly to the listener"),
    ("f-intimate",    "A woman with an intimate and empathetic voice, warm and personal, as if speaking directly to the listener"),
    ("m-calm",        "A man with a calm and grounded voice, steady and reassuring, clear and composed"),
    ("f-calm",        "A woman with a calm and grounded voice, steady and reassuring, clear and composed"),
    ("m-energetic",   "A man with an energetic and engaging voice, dynamic and expressive, keeping the listener's attention"),
    ("f-energetic",   "A woman with an energetic and engaging voice, dynamic and expressive, keeping the listener's attention"),
    ("m-enthusiastic","A man with an enthusiastic and friendly voice, upbeat and warm, genuinely excited about the content"),
    ("f-enthusiastic","A woman with an enthusiastic and friendly voice, upbeat and warm, genuinely excited about the content"),
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
