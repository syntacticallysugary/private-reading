"""JobTracker unit tests.

These tests verify the JobTracker implementation against the following objectives:
1. Verify JobTracker instantiation with/without persistence
2. Verify create_job() returns unique UUIDs
3. Verify state transitions: PENDING → PROCESSING → COMPLETED
4. Verify state transitions: PENDING → PROCESSING → FAILED
5. Verify invalid state transitions are rejected
6. Verify get_job(), list_jobs(), get_jobs_by_status()
7. Verify persistence: save_history() and load_history()
8. Verify thread safety with concurrent access
"""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Optional

import pytest

from private_reading.core.job_tracker import JobTracker, JobRecord


class TestJobTrackerInstantiation:
    """Test Objective 1: Verify JobTracker instantiation with/without persistence."""

    def test_job_tracker_without_persistence(self):
        """Verify JobTracker can be instantiated without persistence."""
        tracker = JobTracker()
        assert tracker is not None
        assert tracker._persistence_path is None
        assert isinstance(tracker._jobs, dict)
        assert len(tracker._jobs) == 0

    def test_job_tracker_with_persistence(self):
        """Verify JobTracker can be instantiated with persistence path."""
        persistence_path = Path("/tmp/test_persistence.json")
        tracker = JobTracker(persistence_path=persistence_path)
        assert tracker is not None
        assert tracker._persistence_path == persistence_path
        assert isinstance(tracker._persistence_path, Path)

    def test_job_tracker_with_persistence_loads_history(self, tmp_path):
        """Verify JobTracker loads existing history on initialization."""
        # Create a tracker and add a job
        tracker1 = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker1.create_job(test_file)

        # Save to persistence
        persistence_path = tmp_path / "history.json"
        tracker1.save_history(persistence_path)

        # Create new tracker and verify it loads history
        tracker2 = JobTracker(persistence_path=persistence_path)
        assert len(tracker2._jobs) == 1
        assert job_id in tracker2._jobs


class TestJobCreation:
    """Test Objective 2: Verify create_job() returns unique UUIDs."""

    def test_create_job_returns_uuid(self, tmp_path):
        """Verify create_job returns a valid UUID string."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        assert isinstance(job_id, str)
        uuid.UUID(job_id)  # Will raise if not valid UUID

    def test_create_job_returns_unique_uuids(self, tmp_path):
        """Verify create_job returns unique UUIDs for each call."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        job_ids = []
        for _ in range(10):
            job_id = tracker.create_job(test_file)
            job_ids.append(job_id)

        # All UUIDs should be unique
        assert len(job_ids) == len(set(job_ids))

    def test_create_job_sets_initial_status(self, tmp_path):
        """Verify create_job sets job status to PENDING."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        job = tracker._jobs[job_id]
        assert job.status == JobTracker.PENDING
        assert job.created_at is not None


class TestStateTransitions_Complete:
    """Test Objective 3: Verify state transitions: PENDING → PROCESSING → COMPLETED."""

    def test_pending_to_processing(self, tmp_path):
        """Verify PENDING → PROCESSING transition works."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Verify initial state
        assert tracker._jobs[job_id].status == JobTracker.PENDING

        # Start the job
        result = tracker.start_job(job_id)
        assert result is True
        assert tracker._jobs[job_id].status == JobTracker.PROCESSING
        assert tracker._jobs[job_id].started_at is not None

    def test_processing_to_completed(self, tmp_path):
        """Verify PROCESSING → COMPLETED transition works."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Start the job
        tracker.start_job(job_id)
        assert tracker._jobs[job_id].status == JobTracker.PROCESSING

        # Complete the job
        result_data = {"output": str(test_file), "duration": 45.2}
        completed = tracker.complete_job(job_id, result_data)
        assert completed is True
        assert tracker._jobs[job_id].status == JobTracker.COMPLETED
        assert tracker._jobs[job_id].completed_at is not None
        assert tracker._jobs[job_id].duration is not None
        assert tracker._jobs[job_id].result == result_data

    def test_full_lifecycle(self, tmp_path):
        """Verify complete lifecycle: PENDING → PROCESSING → COMPLETED."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create job (PENDING)
        job_id = tracker.create_job(test_file)
        assert tracker._jobs[job_id].status == JobTracker.PENDING

        # Start job (PROCESSING)
        tracker.start_job(job_id)
        assert tracker._jobs[job_id].status == JobTracker.PROCESSING

        # Complete job (COMPLETED)
        tracker.complete_job(job_id, {"output": str(test_file)})
        assert tracker._jobs[job_id].status == JobTracker.COMPLETED


class TestStateTransitions_Failed:
    """Test Objective 4: Verify state transitions: PENDING → PROCESSING → FAILED."""

    def test_processing_to_failed(self, tmp_path):
        """Verify PROCESSING → FAILED transition works."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Start the job
        tracker.start_job(job_id)
        assert tracker._jobs[job_id].status == JobTracker.PROCESSING

        # Fail the job
        error_msg = "Test error message"
        failed = tracker.fail_job(job_id, error_msg)
        assert failed is True
        assert tracker._jobs[job_id].status == JobTracker.FAILED
        assert tracker._jobs[job_id].error == error_msg
        assert tracker._jobs[job_id].completed_at is not None

    def test_failed_job_has_duration(self, tmp_path):
        """Verify failed jobs have duration calculated."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        tracker.start_job(job_id)
        tracker.fail_job(job_id, "Test error")

        job = tracker._jobs[job_id]
        assert job.duration is not None
        assert job.duration > 0


class TestInvalidStateTransitions:
    """Test Objective 5: Verify invalid state transitions are rejected."""

    def test_cannot_start_nonexistent_job(self, tmp_path):
        """Verify starting a non-existent job returns False."""
        tracker = JobTracker()
        fake_job_id = "nonexistent-job-id"

        result = tracker.start_job(fake_job_id)
        assert result is False

    def test_cannot_complete_pending_job(self, tmp_path):
        """Verify completing a PENDING job returns False."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Job is PENDING
        assert tracker._jobs[job_id].status == JobTracker.PENDING

        # Try to complete without starting
        result = tracker.complete_job(job_id)
        assert result is False
        assert tracker._jobs[job_id].status == JobTracker.PENDING  # Unchanged

    def test_cannot_fail_pending_job(self, tmp_path):
        """Verify failing a PENDING job returns False."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Job is PENDING
        assert tracker._jobs[job_id].status == JobTracker.PENDING

        # Try to fail without starting
        result = tracker.fail_job(job_id, "Test error")
        assert result is False
        assert tracker._jobs[job_id].status == JobTracker.PENDING  # Unchanged

    def test_cannot_start_already_started_job(self, tmp_path):
        """Verify starting an already-started job returns False."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Start the job
        tracker.start_job(job_id)
        assert tracker._jobs[job_id].status == JobTracker.PROCESSING

        # Try to start again
        result = tracker.start_job(job_id)
        assert result is False
        assert tracker._jobs[job_id].status == JobTracker.PROCESSING  # Unchanged

    def test_cannot_complete_completed_job(self, tmp_path):
        """Verify completing an already-completed job returns False."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Complete the job
        tracker.start_job(job_id)
        tracker.complete_job(job_id, {"output": str(test_file)})
        assert tracker._jobs[job_id].status == JobTracker.COMPLETED

        # Try to complete again
        result = tracker.complete_job(job_id)
        assert result is False
        assert tracker._jobs[job_id].status == JobTracker.COMPLETED  # Unchanged

    def test_cannot_fail_completed_job(self, tmp_path):
        """Verify failing an already-completed job returns False."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Complete the job
        tracker.start_job(job_id)
        tracker.complete_job(job_id, {"output": str(test_file)})
        assert tracker._jobs[job_id].status == JobTracker.COMPLETED

        # Try to fail
        result = tracker.fail_job(job_id, "Test error")
        assert result is False
        assert tracker._jobs[job_id].status == JobTracker.COMPLETED  # Unchanged

    def test_cannot_fail_failed_job(self, tmp_path):
        """Verify failing an already-failed job returns False."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        # Fail the job
        tracker.start_job(job_id)
        tracker.fail_job(job_id, "Test error")
        assert tracker._jobs[job_id].status == JobTracker.FAILED

        # Try to fail again
        result = tracker.fail_job(job_id, "Another error")
        assert result is False
        assert tracker._jobs[job_id].status == JobTracker.FAILED  # Unchanged


class TestJobOperations:
    """Test Objective 6: Verify get_job(), list_jobs(), get_jobs_by_status()."""

    def test_get_job_returns_job(self, tmp_path):
        """Verify get_job() returns the correct job."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        job = tracker.get_job(job_id)
        assert job is not None
        assert job.id == job_id
        assert job.source_file == test_file

    def test_get_job_returns_none_for_nonexistent(self, tmp_path):
        """Verify get_job() returns None for non-existent job."""
        tracker = JobTracker()
        fake_job_id = "nonexistent-job-id"

        job = tracker.get_job(fake_job_id)
        assert job is None

    def test_list_jobs_returns_all(self, tmp_path):
        """Verify list_jobs() returns all jobs."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create multiple jobs
        job_ids = []
        for _ in range(5):
            job_id = tracker.create_job(test_file)
            job_ids.append(job_id)

        # List all jobs
        all_jobs = tracker.list_jobs()
        assert len(all_jobs) == 5
        assert len(all_jobs) == len(job_ids)

    def test_get_jobs_by_status_completed(self, tmp_path):
        """Verify get_jobs_by_status() filters COMPLETED jobs."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create and complete a job
        job_id = tracker.create_job(test_file)
        tracker.start_job(job_id)
        tracker.complete_job(job_id, {"output": str(test_file)})

        # Filter by status
        completed_jobs = tracker.get_jobs_by_status(JobTracker.COMPLETED)
        assert len(completed_jobs) == 1
        assert completed_jobs[0].id == job_id
        assert completed_jobs[0].status == JobTracker.COMPLETED

    def test_get_jobs_by_status_processing(self, tmp_path):
        """Verify get_jobs_by_status() filters PROCESSING jobs."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create and start a job
        job_id = tracker.create_job(test_file)
        tracker.start_job(job_id)

        # Filter by status
        processing_jobs = tracker.get_jobs_by_status(JobTracker.PROCESSING)
        assert len(processing_jobs) == 1
        assert processing_jobs[0].id == job_id
        assert processing_jobs[0].status == JobTracker.PROCESSING

    def test_get_jobs_by_status_pending(self, tmp_path):
        """Verify get_jobs_by_status() filters PENDING jobs."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create a pending job
        job_id = tracker.create_job(test_file)

        # Filter by status
        pending_jobs = tracker.get_jobs_by_status(JobTracker.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].id == job_id
        assert pending_jobs[0].status == JobTracker.PENDING

    def test_get_jobs_by_status_failed(self, tmp_path):
        """Verify get_jobs_by_status() filters FAILED jobs."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create and fail a job
        job_id = tracker.create_job(test_file)
        tracker.start_job(job_id)
        tracker.fail_job(job_id, "Test error")

        # Filter by status
        failed_jobs = tracker.get_jobs_by_status(JobTracker.FAILED)
        assert len(failed_jobs) == 1
        assert failed_jobs[0].id == job_id
        assert failed_jobs[0].status == JobTracker.FAILED

    def test_get_jobs_by_status_empty(self, tmp_path):
        """Verify get_jobs_by_status() returns empty list for no jobs of that status."""
        tracker = JobTracker()

        # Filter for non-existent status
        jobs = tracker.get_jobs_by_status("NONEXISTENT_STATUS")
        assert len(jobs) == 0


class TestPersistence:
    """Test Objective 7: Verify persistence: save_history() and load_history()."""

    def test_save_history_creates_file(self, tmp_path):
        """Verify save_history() creates the persistence file."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        persistence_path = tmp_path / "history.json"
        tracker.save_history(persistence_path)

        assert persistence_path.exists()

    def test_save_history_content(self, tmp_path):
        """Verify save_history() creates valid JSON with job data."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker.create_job(test_file)

        persistence_path = tmp_path / "history.json"
        tracker.save_history(persistence_path)

        # Load and verify content
        with open(persistence_path) as f:
            content = json.load(f)

        assert len(content) == 1
        assert content[0]["id"] == job_id
        assert content[0]["status"] == JobTracker.PENDING

    def test_load_history_loads_jobs(self, tmp_path):
        """Verify load_history() loads jobs from persistence file."""
        # Create tracker and save
        tracker1 = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker1.create_job(test_file)
        tracker1.start_job(job_id)
        tracker1.complete_job(job_id, {"output": str(test_file)})

        persistence_path = tmp_path / "history.json"
        tracker1.save_history(persistence_path)

        # Load with new tracker
        tracker2 = JobTracker()
        tracker2.load_history(persistence_path)

        # Verify jobs loaded
        assert len(tracker2._jobs) == 1
        assert job_id in tracker2._jobs
        loaded_job = tracker2._jobs[job_id]
        assert loaded_job.status == JobTracker.COMPLETED

    def test_persistence_round_trip(self, tmp_path):
        """Verify persistence round-trip preserves all data."""
        tracker1 = JobTracker()
        test_file = tmp_path / "test.mp3"
        job_id = tracker1.create_job(test_file)

        tracker1.start_job(job_id)
        result_data = {"output": str(test_file), "duration": 45.2}
        tracker1.complete_job(job_id, result_data)

        persistence_path = tmp_path / "history.json"
        tracker1.save_history(persistence_path)

        # Load with new tracker
        tracker2 = JobTracker()
        tracker2.load_history(persistence_path)

        # Verify all data preserved
        loaded_job = tracker2._jobs[job_id]
        assert loaded_job.status == JobTracker.COMPLETED
        assert loaded_job.result == result_data
        assert loaded_job.duration is not None
        assert loaded_job.duration > 0


class TestThreadSafety:
    """Test Objective 8: Verify thread safety with concurrent access."""

    def test_concurrent_job_creation(self, tmp_path):
        """Verify concurrent job creation is thread-safe."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        def create_job(num: int) -> str:
            job_id = tracker.create_job(test_file)
            return job_id

        threads = []
        job_ids = []
        lock = threading.Lock()

        for i in range(10):
            t = threading.Thread(target=lambda: job_ids.append(create_job(i)))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All job IDs should be unique
        assert len(job_ids) == 10
        assert len(set(job_ids)) == 10

    def test_concurrent_start_job(self, tmp_path):
        """Verify concurrent start_job calls are thread-safe."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create jobs first
        job_ids = [tracker.create_job(test_file) for _ in range(5)]

        def start_job(job_id: str) -> bool:
            return tracker.start_job(job_id)

        threads = []
        results = []
        lock = threading.Lock()

        for job_id in job_ids:
            t = threading.Thread(target=lambda jid=job_id: results.append(start_job(jid)))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All starts should succeed (first 5 will succeed, rest will fail)
        # But no exceptions should be raised
        assert len(results) == 5

    def test_concurrent_complete_job(self, tmp_path):
        """Verify concurrent complete_job calls are thread-safe."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        # Create and start jobs
        job_ids = []
        for _ in range(5):
            job_id = tracker.create_job(test_file)
            tracker.start_job(job_id)
            job_ids.append(job_id)

        def complete_job(job_id: str) -> bool:
            return tracker.complete_job(job_id, {"output": str(test_file)})

        threads = []
        results = []
        lock = threading.Lock()

        for job_id in job_ids:
            t = threading.Thread(target=lambda jid=job_id: results.append(complete_job(jid)))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All completes should succeed
        assert len(results) == 5
        assert all(results)

    def test_concurrent_mixed_operations(self, tmp_path):
        """Verify mixed concurrent operations are thread-safe."""
        tracker = JobTracker()
        test_file = tmp_path / "test.mp3"

        def operation_sequence(seq_num: int) -> tuple[str, str]:
            try:
                job_id = tracker.create_job(test_file)
                tracker.start_job(job_id)
                tracker.complete_job(job_id, {"output": str(test_file), "seq": seq_num})
                return job_id, "success"
            except Exception as e:
                return str(e), "error"

        threads = []
        results = []
        lock = threading.Lock()

        for i in range(10):
            t = threading.Thread(target=lambda: results.append(operation_sequence(i)))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 10 results
        assert len(results) == 10

        # Count successes
        successes = sum(1 for _, status in results if status == "success")
        assert successes == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
