"""Application entry point for myAudible.

This module provides the MyAudibleApp class that orchestrates all
application components and manages the application lifecycle.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import structlog

from myaudible.config import AppConfig
from myaudible.core.file_watcher import FileWatcher
from myaudible.core.job_tracker import JobTracker
from myaudible.core.pipeline import ProcessingPipeline, ProcessingResult


class MyAudibleApp:
    """Main application entry point for myAudible.

    This class initializes and orchestrates all application components,
    manages the application lifecycle, and handles signal-based shutdown.
    """

    def __init__(self, config: AppConfig):
        """Initialize application with config and all components.

        Args:
            config: Application configuration with paths and settings.
        """
        self.config = config
        self._logger = structlog.get_logger()

        # Initialize ProcessingPipeline
        self.pipeline = ProcessingPipeline(config)

        # Initialize JobTracker immediately
        self.job_tracker: JobTracker = JobTracker(persistence_path=None)

        # FileWatcher initialized in _setup() if watch mode is active
        self.file_watcher: Optional[FileWatcher] = None

        # FIFO queue — inotify enqueues, worker drains one file at a time
        self._file_queue: asyncio.Queue = asyncio.Queue()

        # Ensure input directory exists
        config.input_dir.mkdir(parents=True, exist_ok=True)

    async def run(self):
        """Start the application.

        This method parses command-line arguments, initializes logging,
        starts the file watcher if configured, runs the event loop, and
        handles shutdown signals (SIGINT/SIGTERM).
        """
        self._stop_event = asyncio.Event()

        # Parse command-line arguments
        self._parse_arguments()

        # Initialize logging from config
        self._setup_logging()

        # Log startup information
        self._log_startup()

        # Start file watcher if configured
        if self.file_watcher is not None:
            await self.file_watcher.start()
            self._logger.info("file_watcher.started", directory=str(self.config.input_dir))

        # Set up signal handlers for clean shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._shutdown(sig)),
            )

        # Run event loop
        try:
            await self._main_loop()
        finally:
            await self._shutdown(signal.SIGTERM)

    async def _main_loop(self):
        """Main application event loop.

        This method runs the main application loop, processing files
        either from the file watcher or from command-line arguments.
        """
        # Check for single file mode
        if getattr(self, "_single_file", None):
            single_file = Path(self._single_file)
            if single_file.exists():
                self._logger.info("single_file.mode", file=str(single_file))
                result = await self.process_single_file(single_file)
                self._log_processing_result(result)
            else:
                self._logger.error("single_file.not_found", file=str(single_file))
                sys.exit(1)
            return

        # Watch mode — drain the FIFO queue one file at a time until shutdown
        if getattr(self, "_watch_mode", False):
            self._logger.info("watch.active", directory=str(self.config.input_dir))
            stop_event = getattr(self, "_stop_event", None)
            while stop_event is None or not stop_event.is_set():
                try:
                    file_path = await asyncio.wait_for(
                        self._file_queue.get(), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    continue
                self._logger.info(
                    "queue.processing",
                    file=str(file_path),
                    queue_depth=self._file_queue.qsize(),
                )
                result = await self.process_single_file(file_path)
                self._log_processing_result(result)
                self._file_queue.task_done()
            return

        # Directory mode - process files from input directory
        self._logger.info("directory.mode", directory=str(self.config.input_dir))
        results = await self.pipeline.process_directory(self.config.input_dir)

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        self._logger.info(
            "directory.complete",
            total=len(results),
            successful=successful,
            failed=failed,
        )

    async def _shutdown(self, signal_name: signal.Signals):
        """Handle application shutdown.

        Args:
            signal_name: The signal that triggered shutdown.
        """
        self._logger.info(
            "shutdown.signal",
            signal_name=signal_name.name,
        )

        # Unblock the watch-mode loop
        if hasattr(self, "_stop_event"):
            self._stop_event.set()

        # Stop file watcher if running
        if self.file_watcher is not None:
            await self.file_watcher.stop()

        # Log shutdown summary
        self._log_shutdown()

    async def process_single_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file through the pipeline.

        This method creates a job in JobTracker, executes the pipeline,
        and updates the job status based on the result.

        Args:
            file_path: Path to the file to process.

        Returns:
            ProcessingResult with success status and output path.
        """
        # Create job in JobTracker
        job_id = self.job_tracker.create_job(file_path)
        self._logger.info("job.created", job_id=job_id, file=str(file_path))

        try:
            # Transition job to PROCESSING
            if not self.job_tracker.start_job(job_id):
                raise ValueError(f"Failed to start job {job_id}")

            self._logger.debug("job.started", job_id=job_id)

            # Execute ProcessingPipeline.process_file()
            result = await self.pipeline.process_file(file_path)

            # Update job status (complete or fail)
            if result.success:
                self.job_tracker.complete_job(job_id, result.__dict__)
                self._logger.info(
                    "job.completed",
                    job_id=job_id,
                    file=str(file_path),
                    duration=result.duration,
                )
            else:
                self.job_tracker.fail_job(job_id, result.error or "Unknown error")
                self._logger.error(
                    "job.failed",
                    job_id=job_id,
                    file=str(file_path),
                    error=result.error,
                )

            return result

        except Exception as e:
            # Handle unexpected errors
            self.job_tracker.fail_job(job_id, str(e))
            self._logger.exception(
                "job.failed.unexpected",
                job_id=job_id,
                file=str(file_path),
                error=str(e),
            )
            return ProcessingResult(
                success=False,
                output_path=None,
                error=str(e),
                duration=0.0,
            )

    def health_check(self) -> dict:
        """Return component status and job statistics.

        Returns:
            Dictionary with:
            - pipeline_status: from Pipeline.get_status()
            - job_stats: total jobs, jobs by status
            - component_health: from pipeline health checks
        """
        # Get pipeline status
        pipeline_status = self.pipeline.get_status()

        # Get job statistics from JobTracker
        job_stats = {
            "total": len(self.job_tracker.list_jobs()),
            "pending": len(self.job_tracker.get_jobs_by_status(JobTracker.PENDING)),
            "processing": len(self.job_tracker.get_jobs_by_status(JobTracker.PROCESSING)),
            "completed": len(self.job_tracker.get_jobs_by_status(JobTracker.COMPLETED)),
            "failed": len(self.job_tracker.get_jobs_by_status(JobTracker.FAILED)),
        }

        # Get component health from pipeline
        component_health = pipeline_status.component_health

        return {
            "pipeline_status": {
                "state": pipeline_status.state,
                "active_jobs": pipeline_status.active_jobs,
            },
            "job_stats": job_stats,
            "component_health": component_health,
        }

    def _on_file_detected(self, file_path: Path) -> None:
        """Enqueue a detected file for sequential processing."""
        self._file_queue.put_nowait(file_path)
        self._logger.info(
            "queue.enqueued",
            file=str(file_path),
            queue_depth=self._file_queue.qsize(),
        )

    def _parse_arguments(self):
        """Parse command-line arguments."""
        self._watch_mode = "-w" in sys.argv or "--watch" in sys.argv
        self._single_file = None

        for flag in ("--single", "--input", "-i"):
            if flag in sys.argv:
                idx = sys.argv.index(flag)
                if idx + 1 < len(sys.argv):
                    candidate = Path(sys.argv[idx + 1])
                    if candidate.is_file():
                        self._single_file = str(candidate)
                        break

        if self._watch_mode and self.file_watcher is None:
            self.file_watcher = FileWatcher(
                input_path=self.config.input_dir,
                callback=self._on_file_detected,
            )
        if self.job_tracker is None:
            self.job_tracker = JobTracker(persistence_path=None)

    def _setup_logging(self):
        """Configure structured logging from config."""
        from myaudible.utils.logging import setup_logging

        setup_logging(self.config)

    def _log_startup(self):
        """Log application startup information."""
        self._logger.info(
            "startup",
            version="1.0.0",
            input_dir=str(self.config.input_dir),
            watch_mode=getattr(self, "_watch_mode", False),
        )

    def _log_processing_result(self, result: ProcessingResult):
        """Log processing result.

        Args:
            result: ProcessingResult from pipeline.
        """
        if result.success:
            self._logger.info(
                "processing.success",
                output=str(result.output_path),
                duration=result.duration,
            )
        else:
            self._logger.error(
                "processing.failed",
                error=result.error,
                duration=result.duration,
            )

    def _log_shutdown(self):
        """Log shutdown summary."""
        health = self.health_check()
        self._logger.info(
            "shutdown.complete",
            pipeline_state=health["pipeline_status"]["state"],
            total_jobs=health["job_stats"]["total"],
            completed=health["job_stats"]["completed"],
            failed=health["job_stats"]["failed"],
        )


# Main entry point for running the application
def main():
    """Main entry point for myAudible application."""
    from myaudible.config import AppConfig

    # Load configuration
    config = AppConfig()

    # Create and run application
    app = MyAudibleApp(config)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
