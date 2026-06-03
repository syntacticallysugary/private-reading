"""Benchmark Fish Speech vs Qwen3-TTS-Base inference speed.

Sends identical text chunks to both endpoints sequentially (GPU is single-threaded),
discards the first run as a warm-up, then reports per-chunk timing statistics.
"""

import asyncio
import statistics
import time
from dataclasses import dataclass, field

import aiohttp

# ── Endpoints ────────────────────────────────────────────────────────────────

FISH_ENDPOINT = "http://localhost:8013/v1/tts"
QWEN_ENDPOINT = "http://localhost:8014/v1/audio/speech"

FISH_REFERENCE_ID = ""  # set to your registered voice ID if you want cloned voice

# ── Test corpus ──────────────────────────────────────────────────────────────
# Representative 400-char chunks covering mixed sentence types

CHUNKS = [
    (
        "Cost optimization is not about choosing the cheapest option but about aligning "
        "cost with usage. One approach is to use serverless services like Lambda, which "
        "charge only for execution time. This eliminates idle resource costs."
    ),
    (
        "For predictable workloads, Reserved Instances or Savings Plans can significantly "
        "reduce EC2 costs. For flexible or fault-tolerant workloads, Spot Instances provide "
        "substantial savings. The key is matching the pricing model to the workload pattern."
    ),
    (
        "Engineering design can be framed as a process that involves taking iterative design "
        "steps informed by design thinking and reasoning. In an effort to assist or automate "
        "the design process, research has widely explored the implementation of AI systems."
    ),
    (
        "The three systems demonstrated comparable effectiveness in completing the design task. "
        "Overall, all thirty runs generated valid final designs within the maximum allowed steps. "
        "The system with the lowest design capacity range also showed the highest consistency."
    ),
    (
        "Security in cloud architecture requires defence in depth: encrypting data at rest and "
        "in transit, enforcing least-privilege IAM policies, and logging all API calls to "
        "CloudTrail. No single control is sufficient; layers of controls are essential."
    ),
]

WARMUP_RUNS = 1
TIMED_RUNS = len(CHUNKS)

# ── Benchmark logic ───────────────────────────────────────────────────────────


@dataclass
class Result:
    name: str
    times_s: list[float] = field(default_factory=list)
    errors: int = 0


async def fish_request(session: aiohttp.ClientSession, text: str) -> float:
    payload = {
        "text": text,
        "format": "wav",
        "references": [],
        "streaming": False,
        "temperature": 0.8,
        "top_p": 0.8,
        "repetition_penalty": 1.1,
    }
    if FISH_REFERENCE_ID:
        payload["reference_id"] = FISH_REFERENCE_ID
    t0 = time.perf_counter()
    async with session.post(
        FISH_ENDPOINT, json=payload, timeout=aiohttp.ClientTimeout(total=600)
    ) as resp:
        resp.raise_for_status()
        await resp.read()
    return time.perf_counter() - t0


async def qwen_request(session: aiohttp.ClientSession, text: str) -> float:
    payload = {
        "input": text,
        "model": "qwen3-tts",
        "response_format": "wav",
        "temperature": 0.7,
    }
    t0 = time.perf_counter()
    async with session.post(
        QWEN_ENDPOINT, json=payload, timeout=aiohttp.ClientTimeout(total=600)
    ) as resp:
        resp.raise_for_status()
        await resp.read()
    return time.perf_counter() - t0


async def run_engine(name: str, fn, chunks: list[str]) -> Result:
    result = Result(name=name)
    async with aiohttp.ClientSession() as session:
        print(f"\n{'─'*50}")
        print(f"  {name}")
        print(f"{'─'*50}")

        # Warm-up
        for i in range(WARMUP_RUNS):
            print(f"  [warm-up {i+1}/{WARMUP_RUNS}] chunk 0 ... ", end="", flush=True)
            try:
                t = await fn(session, chunks[0])
                print(f"{t:.1f}s  (discarded)")
            except Exception as exc:
                print(f"ERROR: {exc}")

        # Timed runs
        for i, chunk in enumerate(chunks):
            chars = len(chunk)
            print(f"  [run {i+1}/{len(chunks)}] {chars} chars ... ", end="", flush=True)
            try:
                t = await fn(session, chunk)
                result.times_s.append(t)
                print(f"{t:.2f}s  ({chars/t:.0f} chars/s)")
            except Exception as exc:
                result.errors += 1
                print(f"ERROR: {exc}")

    return result


def report(results: list[Result]) -> None:
    print(f"\n{'═'*50}")
    print("  RESULTS")
    print(f"{'═'*50}")
    for r in results:
        if not r.times_s:
            print(f"\n  {r.name}: no successful runs")
            continue
        avg = statistics.mean(r.times_s)
        med = statistics.median(r.times_s)
        mn = min(r.times_s)
        mx = max(r.times_s)
        total_chars = sum(len(c) for c in CHUNKS[: len(r.times_s)])
        total_time = sum(r.times_s)
        print(f"\n  {r.name}")
        print(f"    avg     {avg:.2f}s")
        print(f"    median  {med:.2f}s")
        print(f"    min     {mn:.2f}s")
        print(f"    max     {mx:.2f}s")
        print(f"    throughput  {total_chars/total_time:.0f} chars/s overall")
        if r.errors:
            print(f"    errors  {r.errors}")

    if len(results) == 2 and results[0].times_s and results[1].times_s:
        a, b = results
        ratio = statistics.mean(a.times_s) / statistics.mean(b.times_s)
        faster = a.name if ratio < 1 else b.name
        slower = b.name if ratio < 1 else a.name
        print(f"\n  {'─'*48}")
        print(f"  {faster} is {max(ratio, 1/ratio):.2f}x faster than {slower} on average")


async def main() -> None:
    print("TTS Inference Benchmark")
    print(f"  Chunks: {len(CHUNKS)}  |  Warm-up runs: {WARMUP_RUNS}")

    fish_result = await run_engine("Fish Speech", fish_request, CHUNKS)
    qwen_result = await run_engine("Qwen3-TTS-Base", qwen_request, CHUNKS)

    report([fish_result, qwen_result])


if __name__ == "__main__":
    asyncio.run(main())
