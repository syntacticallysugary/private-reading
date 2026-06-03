"""FastAPI web server for the Private Reading web interface.

Endpoints:
    POST /api/jobs          Accept text, run security check, start TTS job.
    GET  /api/jobs/{id}     Poll job status and chunk progress.
    GET  /api/jobs/{id}/audio  Stream the completed WAV file.
    GET  /                  Serve the single-page UI.

Run:
    python -m web.server
    uvicorn web.server:app --reload --port 7860
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from private_reading.config import ProcessingConfig, SemaphoreConfig, TTSConfig
from web.pipeline_runner import run_pipeline
from web.security import check_text

app = FastAPI(title="Private Reading", docs_url=None, redoc_url=None)

_STATIC_DIR = Path(__file__).parent / "static"
_OUTPUT_DIR = Path("output/web_jobs")

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = asyncio.Lock()

_tts = TTSConfig()
_processing = ProcessingConfig()
_semaphore = SemaphoreConfig()


@app.on_event("startup")
async def _startup() -> None:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SubmitRequest(BaseModel):
    """Request body for POST /api/jobs."""

    text: str = Field(..., min_length=1, max_length=100_000)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> HTMLResponse:
    """Serve the single-page UI."""
    return HTMLResponse((_STATIC_DIR / "index.html").read_text())


@app.post("/api/jobs", status_code=202)
async def create_job(request: SubmitRequest, background_tasks: BackgroundTasks) -> dict:
    """Validate text, create a job, and start the TTS pipeline in the background.

    Args:
        request: Contains the text to convert.
        background_tasks: FastAPI background task runner.

    Returns:
        Dict with job_id.

    Raises:
        HTTPException 422: If the text fails the security check.
    """
    result = check_text(request.text)
    if not result.is_safe:
        raise HTTPException(
            status_code=422,
            detail=result.warnings[0] if result.warnings else "Content rejected by security filter.",
        )

    job_id = str(uuid.uuid4())
    async with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "chunks_done": 0,
            "chunks_total": None,
            "error": None,
        }

    background_tasks.add_task(_process_job, job_id, request.text)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    """Return the current status and progress of a job.

    Args:
        job_id: UUID of the job.

    Returns:
        Dict with status, chunks_done, chunks_total, and error fields.

    Raises:
        HTTPException 404: If job_id is unknown.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {k: v for k, v in job.items() if k != "_wav_path"}


@app.get("/api/jobs/{job_id}/audio")
async def get_audio(job_id: str) -> FileResponse:
    """Stream the completed WAV file for a finished job.

    Args:
        job_id: UUID of the job.

    Returns:
        FileResponse streaming the WAV.

    Raises:
        HTTPException 404: If job not found or audio not yet ready.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(status_code=404, detail=f"Audio not ready ({job['status']}).")
    return FileResponse(
        job["_wav_path"],
        media_type="audio/wav",
        filename=f"private-reading-{job_id[:8]}.wav",
    )


async def _process_job(job_id: str, text: str) -> None:
    """Background task: run the TTS pipeline and update job state."""
    async with _jobs_lock:
        _jobs[job_id]["status"] = "processing"

    def _on_progress(done: int, total: int) -> None:
        _jobs[job_id]["chunks_done"] = done
        _jobs[job_id]["chunks_total"] = total

    try:
        wav_path = await run_pipeline(
            text,
            _OUTPUT_DIR,
            job_id,
            tts=_tts,
            processing=_processing,
            semaphore=_semaphore,
            on_progress=_on_progress,
        )
        async with _jobs_lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["_wav_path"] = str(wav_path)
    except Exception as exc:
        async with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(exc)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.server:app", host="0.0.0.0", port=7860, reload=True)
