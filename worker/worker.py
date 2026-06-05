"""Worker for Private Reading — polls the cloud API and runs the Qwen3-TTS-Base pipeline."""

import asyncio
import json
import logging
import os
import struct
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import aiohttp.web
import oci
import oci.object_storage

from private_reading.config import ProcessingConfig, SemaphoreConfig, TTSConfig
from private_reading.core.chunk_manager import ChunkManager
from private_reading.core.tts_client import TTSClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("worker")

API_BASE_URL = os.environ["API_BASE_URL"].rstrip("/")
WORKER_API_KEY = os.environ["WORKER_API_KEY"]
BUCKET_NAME = os.environ["AUDIOBOOKS_BUCKET"]
OCI_NAMESPACE = os.environ["OCI_NAMESPACE"]
OCI_REGION = os.environ["OCI_REGION"]
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "8765"))
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

_notify_event = asyncio.Event()

_tts_cfg = TTSConfig()
_proc_cfg = ProcessingConfig()
_chunk_manager = ChunkManager(
    max_chars=_proc_cfg.chunk_size,
    overlap_ratio=_proc_cfg.overlap_ratio,
)
_semaphore_size = SemaphoreConfig().size


def _oci_client() -> oci.object_storage.ObjectStorageClient:
    config_path = os.environ.get("OCI_CONFIG_PATH", "~/.oci/config")
    return oci.object_storage.ObjectStorageClient(oci.config.from_file(config_path))


_os_client = _oci_client()


def _headers() -> dict:
    return {"X-Worker-Token": WORKER_API_KEY, "Content-Type": "application/json"}


def _fix_wav_header(data: bytes) -> bytes:
    """Patch placeholder RIFF chunk sizes (0xFFFFFFFF sentinel) written by streaming TTS servers."""
    if len(data) < 44 or data[:4] != b"RIFF":
        return data
    if struct.unpack_from("<I", data, 4)[0] != 0xFFFFFFFF:
        return data
    buf = bytearray(data)
    struct.pack_into("<I", buf, 4, len(buf) - 8)
    struct.pack_into("<I", buf, 40, len(buf) - 44)
    return bytes(buf)


# ── API helpers ────────────────────────────────────────────────────────────────


async def poll_pending(session: aiohttp.ClientSession) -> Optional[dict]:
    try:
        async with session.get(
            f"{API_BASE_URL}/worker/jobs/pending",
            headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            return (await resp.json()).get("job")
    except Exception as exc:
        logger.error("poll error: %s", exc)
        return None


async def claim_job(session: aiohttp.ClientSession, job_id: str) -> bool:
    try:
        async with session.post(
            f"{API_BASE_URL}/worker/jobs/{job_id}/claim",
            headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            return resp.status == 200
    except Exception as exc:
        logger.error("claim error %s: %s", job_id, exc)
        return False


async def complete_job(session: aiohttp.ClientSession, job_id: str, audio_path: str) -> None:
    try:
        async with session.post(
            f"{API_BASE_URL}/worker/jobs/{job_id}/complete",
            headers=_headers(),
            json={"audio_path": audio_path},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
    except Exception as exc:
        logger.error("complete error %s: %s", job_id, exc)


async def progress_job(
    session: aiohttp.ClientSession, job_id: str, chunks_done: int, chunks_total: int
) -> None:
    try:
        async with session.post(
            f"{API_BASE_URL}/worker/jobs/{job_id}/progress",
            headers=_headers(),
            json={"chunks_done": chunks_done, "chunks_total": chunks_total},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("progress error %s: %s", job_id, exc)


async def fail_job(session: aiohttp.ClientSession, job_id: str, error: str) -> None:
    try:
        async with session.post(
            f"{API_BASE_URL}/worker/jobs/{job_id}/fail",
            headers=_headers(),
            json={"error": error},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
    except Exception as exc:
        logger.error("fail error %s: %s", job_id, exc)


# ── Processing ─────────────────────────────────────────────────────────────────


def _ocs_get(object_name: str) -> bytes | None:
    try:
        resp = _os_client.get_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=object_name,
        )
        return resp.data.content
    except Exception as exc:
        if "404" in str(exc) or "ObjectNotFound" in str(exc) or "NoSuchKey" in str(exc):
            return None
        raise


def _ocs_put(object_name: str, data: bytes, content_type: str = "application/json") -> None:
    import io as _io

    _os_client.put_object(
        namespace_name=OCI_NAMESPACE,
        bucket_name=BUCKET_NAME,
        object_name=object_name,
        put_object_body=_io.BytesIO(data),
        content_type=content_type,
    )


async def get_or_register_voice(session: aiohttp.ClientSession, user_id: str) -> str:
    """Return TTS reference_id for the user, registering if pending.

    Returns the user_id if active, the global config reference_id otherwise.
    """
    tts_base = f"{urlparse(_tts_cfg.endpoint).scheme}://{urlparse(_tts_cfg.endpoint).netloc}"
    meta_key = f"voices/{user_id}/metadata.json"
    sample_key = f"voices/{user_id}/sample"
    loop = asyncio.get_running_loop()

    try:
        raw = await loop.run_in_executor(None, _ocs_get, meta_key)
        if raw is None:
            return _tts_cfg.reference_id
        meta = json.loads(raw)
    except Exception:
        logger.warning("voice metadata read failed for %s", user_id[:8])
        return _tts_cfg.reference_id

    if meta.get("status") == "active":
        return user_id

    if meta.get("status") != "pending":
        return _tts_cfg.reference_id

    logger.info("registering voice for user %s", user_id[:8])
    try:
        sample_bytes = await loop.run_in_executor(None, _ocs_get, sample_key)
        if not sample_bytes:
            raise RuntimeError("sample not found in OCS")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raw_path = tmp / "sample"
            raw_path.write_bytes(sample_bytes)
            wav_path = tmp / "sample.wav"

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-i",
                str(raw_path),
                "-ar",
                "44100",
                "-ac",
                "1",
                "-f",
                "wav",
                str(wav_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, ffmpeg_err = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg transcode: {ffmpeg_err.decode()}")

            wav_bytes = wav_path.read_bytes()

        form = aiohttp.FormData()
        form.add_field("id", user_id)
        form.add_field("audio", wav_bytes, filename="sample.wav", content_type="audio/wav")
        form.add_field("transcript", meta.get("transcript", ""))
        async with session.post(
            f"{tts_base}/v1/references/add",
            data=form,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 409:
                resp.raise_for_status()

        meta["status"] = "active"
        await loop.run_in_executor(None, _ocs_put, meta_key, json.dumps(meta).encode())
        logger.info("voice registration complete for user %s", user_id[:8])
        return user_id

    except Exception:
        logger.exception("voice registration failed for user %s — using default", user_id[:8])
        return _tts_cfg.reference_id


def _upload(local_path: Path, object_name: str) -> None:
    with open(local_path, "rb") as f:
        _os_client.put_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            put_object_body=f,
            content_type="audio/ogg",
        )


async def process_job(session: aiohttp.ClientSession, job: dict) -> None:
    job_id = job["job_id"]
    user_id = job["user_id"]
    text = job["text"]
    logger.info("processing job %s (%d chars)", job_id, len(text))

    reference_id = await get_or_register_voice(session, user_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        try:
            # 1. Chunk
            chunks = await _chunk_manager.chunk(text)
            logger.info("job %s: %d chunks", job_id, len(chunks))

            # 2. TTS — parallel with semaphore, progress reported after each chunk
            chunks_total = len(chunks)
            chunks_done = 0
            semaphore = asyncio.Semaphore(_semaphore_size)
            progress_lock = asyncio.Lock()

            async def tts_chunk(chunk: str, idx: int) -> tuple[int, Path]:
                nonlocal chunks_done
                async with semaphore:
                    audio = await tts.generate_speech(chunk)
                path = tmp / f"chunk_{idx:04d}.wav"
                path.write_bytes(_fix_wav_header(audio))
                async with progress_lock:
                    chunks_done += 1
                    done = chunks_done
                await progress_job(session, job_id, done, chunks_total)
                return idx, path

            async with TTSClient(
                endpoint=_tts_cfg.endpoint,
                provider=_tts_cfg.provider,
                model=_tts_cfg.model,
                temperature=_tts_cfg.temperature,
                reference_id=reference_id,
                retry_attempts=_tts_cfg.retry_attempts,
                timeout_seconds=_tts_cfg.timeout_seconds,
            ) as tts:
                results = await asyncio.gather(
                    *[tts_chunk(c, i) for i, c in enumerate(chunks)],
                    return_exceptions=True,
                )

            failures = [(i, r) for i, r in enumerate(results) if isinstance(r, Exception)]
            if failures:
                sample = "; ".join(f"chunk {i}: {r}" for i, r in failures[:3])
                raise RuntimeError(f"{len(failures)}/{chunks_total} chunks failed: {sample}")

            ok = (r for r in results if not isinstance(r, BaseException))
            wav_paths = [p for _, p in sorted(ok)]  # type: ignore[misc]

            # 3. Stitch to Opus
            output_ogg = tmp / "output.ogg"
            concat_list = tmp / "concat.txt"
            concat_list.write_text("\n".join(f"file '{p}'" for p in wav_paths))

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:a",
                "libopus",
                "-b:a",
                "64k",
                "-y",
                str(output_ogg),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg: {stderr.decode()}")

            # 4. Upload (blocking I/O → executor so it doesn't block the loop)
            object_name = f"audio/{user_id}/{job_id}.ogg"
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _upload, output_ogg, object_name)

            await complete_job(session, job_id, object_name)
            logger.info("job %s done → %s", job_id, object_name)

        except Exception:
            logger.exception("job %s failed", job_id)
            import traceback

            await fail_job(session, job_id, traceback.format_exc(limit=3))


# ── Webhook server ─────────────────────────────────────────────────────────────


async def _handle_notify(request: aiohttp.web.Request) -> aiohttp.web.Response:
    if request.headers.get("X-Webhook-Secret") != WEBHOOK_SECRET:
        logger.warning("webhook: unauthorized request from %s", request.remote)
        return aiohttp.web.Response(status=401)
    _notify_event.set()
    return aiohttp.web.Response(status=204)


async def _run_webhook_server() -> None:
    app = aiohttp.web.Application()
    app.router.add_post("/notify", _handle_notify)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(
        runner, "0.0.0.0", WEBHOOK_PORT
    )  # nosec B104 — hostNetwork pod, all interfaces intentional
    await site.start()
    logger.info("webhook server listening on :%d", WEBHOOK_PORT)
    await asyncio.Future()


# ── Main loop ──────────────────────────────────────────────────────────────────


async def _register_pending_voices(session: aiohttp.ClientSession) -> None:
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: _os_client.list_objects(
                namespace_name=OCI_NAMESPACE,
                bucket_name=BUCKET_NAME,
                prefix="voices/",
                fields="name",
            ),
        )
        for obj in resp.data.objects:
            if not obj.name.endswith("/metadata.json"):
                continue
            parts = obj.name.split("/")
            if len(parts) != 3:
                continue
            user_id = parts[1]
            raw = await loop.run_in_executor(None, _ocs_get, obj.name)
            if not raw:
                continue
            if json.loads(raw).get("status") == "pending":
                await get_or_register_voice(session, user_id)
    except Exception:
        logger.exception("error scanning for pending voices")


async def run() -> None:
    logger.info("worker started — polling %s every %ds", API_BASE_URL, POLL_INTERVAL)
    async with aiohttp.ClientSession() as session:
        while True:
            job = await poll_pending(session)
            if job:
                if await claim_job(session, job["job_id"]):
                    await process_job(session, job)
                else:
                    logger.warning("failed to claim job %s (already taken)", job["job_id"])
            else:
                await _register_pending_voices(session)
                try:
                    await asyncio.wait_for(_notify_event.wait(), timeout=POLL_INTERVAL)
                except asyncio.TimeoutError:
                    pass
                _notify_event.clear()


if __name__ == "__main__":
    asyncio.run(asyncio.gather(run(), _run_webhook_server()))
