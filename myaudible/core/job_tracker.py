"""Job tracking module for myAudible."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class JobRecord:
    """Record of a job's execution state and metadata."""

    id: str
    source_file: Path
    status: str  # PENDING, PROCESSING, COMPLETED, FAILED
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    result: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert the JobRecord to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_file": str(self.source_file),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "error": self.error,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JobRecord:
        """Create a JobRecord from a dictionary."""
        created_at = datetime.fromisoformat(data["created_at"])
        started_at = (
            datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None
        )
        completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )

        return cls(
            id=data["id"],
            source_file=Path(data["source_file"]),
            status=data["status"],
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            duration=data.get("duration"),
            error=data.get("error"),
            result=data.get("result"),
        )


class JobTracker:
    """Tracks job execution state and provides persistence."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def __init__(self, persistence_path: Optional[Path] = None):
        """Initialize job tracker with optional file persistence.

        Args:
            persistence_path: Optional path to store/load job history.
        """
        self._jobs: dict[str, JobRecord] = {}
        self._persistence_path = persistence_path
        self._lock = threading.Lock()

        # Load existing history if persistence is enabled
        if persistence_path is not None and persistence_path.exists():
            self.load_history(persistence_path)

    def _get_utc_now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)

    def create_job(self, source_file: Path) -> str:
        """Create a new job and return its unique ID.

        Args:
            source_file: Path to the source file being processed.

        Returns:
            The unique job ID (UUID).
        """
        with self._lock:
            job_id = str(uuid.uuid4())
            created_at = self._get_utc_now()

            job_record = JobRecord(
                id=job_id,
                source_file=source_file,
                status=self.PENDING,
                created_at=created_at,
            )

            self._jobs[job_id] = job_record

            # Save to persistence if enabled
            if self._persistence_path is not None:
                self.save_history(self._persistence_path)

            return job_id

    def start_job(self, job_id: str) -> bool:
        """Transition job from PENDING to PROCESSING.

        Args:
            job_id: The job ID to start.

        Returns:
            True if the transition was successful, False otherwise.
        """
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]

            # Validate state transition: only PENDING -> PROCESSING
            if job.status != self.PENDING:
                return False

            job.status = self.PROCESSING
            job.started_at = self._get_utc_now()

            # Save to persistence if enabled
            if self._persistence_path is not None:
                self.save_history(self._persistence_path)

            return True

    def complete_job(self, job_id: str, result: Optional[dict] = None) -> bool:
        """Transition job from PROCESSING to COMPLETED.

        Args:
            job_id: The job ID to complete.
            result: Optional result data to store.

        Returns:
            True if the transition was successful, False otherwise.
        """
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]

            # Validate state transition: only PROCESSING -> COMPLETED
            if job.status != self.PROCESSING:
                return False

            job.status = self.COMPLETED
            job.completed_at = self._get_utc_now()

            # Calculate duration
            if job.started_at is not None:
                duration = (
                    job.completed_at - job.started_at
                ).total_seconds()
                job.duration = duration

            job.result = result

            # Save to persistence if enabled
            if self._persistence_path is not None:
                self.save_history(self._persistence_path)

            return True

    def fail_job(self, job_id: str, error: str) -> bool:
        """Transition job from PROCESSING to FAILED.

        Args:
            job_id: The job ID to fail.
            error: Error message describing the failure.

        Returns:
            True if the transition was successful, False otherwise.
        """
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]

            # Validate state transition: only PROCESSING -> FAILED
            if job.status != self.PROCESSING:
                return False

            job.status = self.FAILED
            job.completed_at = self._get_utc_now()

            # Calculate duration
            if job.started_at is not None:
                duration = (
                    job.completed_at - job.started_at
                ).total_seconds()
                job.duration = duration

            job.error = error

            # Save to persistence if enabled
            if self._persistence_path is not None:
                self.save_history(self._persistence_path)

            return True

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Get a specific job by ID.

        Args:
            job_id: The job ID to retrieve.

        Returns:
            The JobRecord if found, None otherwise.
        """
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobRecord]:
        """List all jobs.

        Returns:
            List of all JobRecord objects.
        """
        with self._lock:
            return list(self._jobs.values())

    def get_jobs_by_status(self, status: str) -> list[JobRecord]:
        """Get jobs filtered by status.

        Args:
            status: The status to filter by (PENDING, PROCESSING, COMPLETED, FAILED).

        Returns:
            List of JobRecord objects matching the status.
        """
        with self._lock:
            return [job for job in self._jobs.values() if job.status == status]

    def save_history(self, path: Path) -> None:
        """Save job history to JSON file.

        Args:
            path: Path to save the history file.
        """
        with self._lock:
            jobs_data = [job.to_dict() for job in self._jobs.values()]

            with open(path, "w") as f:
                json.dump(jobs_data, f, indent=2)

    def load_history(self, path: Path) -> None:
        """Load job history from JSON file.

        Args:
            path: Path to the history file.
        """
        with open(path, "r") as f:
            jobs_data = json.load(f)

        for data in jobs_data:
            job = JobRecord.from_dict(data)
            self._jobs[job.id] = job
