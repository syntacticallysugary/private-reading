"""FastAPI job store service — SQLite backend for Private Reading."""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

DB_PATH = os.environ.get("DB_PATH", "/data/jobs.db")
TOKEN = os.environ["JOB_STORE_TOKEN"]

app = FastAPI(title="job-store")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_db() -> None:
    with _db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id          TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                text            TEXT NOT NULL,
                text_length     INTEGER NOT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                error           TEXT DEFAULT '',
                audio_path      TEXT DEFAULT '',
                audio_expires_at TEXT DEFAULT '',
                chunks_done     INTEGER DEFAULT 0,
                chunks_total    INTEGER DEFAULT 0
            )
        """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_created ON jobs (user_id, created_at DESC)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status_created ON jobs (status, created_at)")


_init_db()


@app.middleware("http")
async def _require_auth(request: Request, call_next):
    if request.headers.get("x-job-store-token", "") != TOKEN:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)


def _fetch_row(conn: sqlite3.Connection, job_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


class JobCreate(BaseModel):
    """Body for POST /jobs."""

    user_id: str
    job_id: str | None = None
    text: str


class CompleteBody(BaseModel):
    """Body for POST /jobs/{job_id}/complete."""

    audio_path: str


class FailBody(BaseModel):
    """Body for POST /jobs/{job_id}/fail."""

    error: str = "unknown"


class ProgressBody(BaseModel):
    """Body for POST /jobs/{job_id}/progress."""

    chunks_done: int
    chunks_total: int


# Routes are declared most-specific first to prevent parameterised paths from
# swallowing literal segments (e.g. /jobs/pending must come before /jobs/{job_id}).


@app.post("/jobs", status_code=201)
def create_job(body: JobCreate):
    now = _now()
    job_id = body.job_id or uuid.uuid4().hex[:24]
    with _db() as conn:
        conn.execute(
            """INSERT INTO jobs
               (job_id, user_id, status, text, text_length, created_at, updated_at)
               VALUES (?, ?, 'pending', ?, ?, ?, ?)""",
            (job_id, body.user_id, body.text, len(body.text), now, now),
        )
        return _fetch_row(conn, job_id)


@app.get("/jobs/pending")
def get_pending():
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at LIMIT 1"
        ).fetchone()
        return {"job": dict(row) if row else None}


@app.get("/jobs/user/{user_id}/current")
def get_current(user_id: str):
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if not row:
            return JSONResponse({"error": "No current job"}, status_code=404)
        return dict(row)


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with _db() as conn:
        job = _fetch_row(conn, job_id)
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        return job


@app.delete("/jobs/{user_id}/{job_id}")
def delete_job(user_id: str, job_id: str):
    with _db() as conn:
        conn.execute("DELETE FROM jobs WHERE user_id = ? AND job_id = ?", (user_id, job_id))
        return {"deleted": True}


@app.post("/jobs/{job_id}/claim")
def claim_job(job_id: str):
    with _db() as conn:
        job = _fetch_row(conn, job_id)
        if not job:
            return JSONResponse({"error": "Job not found"}, status_code=404)
        if job["status"] != "pending":
            return JSONResponse({"error": f"Job not pending: {job['status']}"}, status_code=409)
        conn.execute(
            "UPDATE jobs SET status = 'processing', updated_at = ? WHERE job_id = ?",
            (_now(), job_id),
        )
        return _fetch_row(conn, job_id)


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str, body: CompleteBody):
    with _db() as conn:
        if not _fetch_row(conn, job_id):
            return JSONResponse({"error": "Job not found"}, status_code=404)
        conn.execute(
            "UPDATE jobs SET status = 'complete', audio_path = ?, updated_at = ? WHERE job_id = ?",
            (body.audio_path, _now(), job_id),
        )
        return {"ok": True}


@app.post("/jobs/{job_id}/fail")
def fail_job(job_id: str, body: FailBody):
    with _db() as conn:
        if not _fetch_row(conn, job_id):
            return JSONResponse({"error": "Job not found"}, status_code=404)
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ?, updated_at = ? WHERE job_id = ?",
            (body.error, _now(), job_id),
        )
        return {"ok": True}


@app.post("/jobs/{job_id}/progress")
def progress_job(job_id: str, body: ProgressBody):
    with _db() as conn:
        if not _fetch_row(conn, job_id):
            return JSONResponse({"error": "Job not found"}, status_code=404)
        conn.execute(
            """UPDATE jobs SET chunks_done = ?, chunks_total = ?, updated_at = ?
               WHERE job_id = ?""",
            (body.chunks_done, body.chunks_total, _now(), job_id),
        )
        return {"ok": True}
