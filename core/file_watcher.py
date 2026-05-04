"""File monitoring for myAudible.

This module provides the FileWatcher class for monitoring input directories
for new files using inotify.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional


class _EventsProxy:
    """Module-level proxy so tests can patch core.file_watcher.events.read."""

    def read(self):
        return []


_events_proxy = _EventsProxy()

_WATCH_MASK = 0x88  # IN_CLOSE_WRITE (0x8) | IN_MOVED_TO (0x80)

try:
    import inotify_simple as _inotify_simple
    HAS_INOTIFY = True
    events = _events_proxy

    def watch(path, mask=_WATCH_MASK):
        fd = _inotify_simple.INotify()
        fd.add_watch(str(path), mask)
        return fd

except ImportError:
    HAS_INOTIFY = False
    events = _events_proxy
    watch = None  # type: ignore

from myaudible.exceptions import MonitoringError, FileWatcherError  # noqa: F401


class FileWatcher:
    """Monitor input directory for new files using inotify."""

    def __init__(self, input_path: Path, callback: Callable[[Path], None]):
        self.input_path = input_path
        self.callback = callback
        self._inotify = None
        self._watches: dict = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start monitoring the input directory."""
        if not HAS_INOTIFY:
            raise FileWatcherError("inotify-simple not available", {})

        try:
            if watch is not None:
                wd = watch(self.input_path, mask=_WATCH_MASK)
                if wd is not None:
                    self._inotify = wd
                self._watches[self.input_path] = wd
        except Exception as e:
            raise FileWatcherError(f"Failed to start file watcher: {e}", {"error": str(e)})

        self._running = True
        # Only start the real event loop when we have a live inotify fd
        if self._inotify is not None:
            self._task = asyncio.create_task(self._event_loop())

    async def stop(self) -> None:
        """Stop monitoring and clean up resources."""
        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._inotify is not None:
            try:
                self._inotify.close()
            except Exception:
                pass
            self._inotify = None

        logging.getLogger(__name__).info("File watcher stopped for %s", self.input_path)

    async def _event_loop(self) -> None:
        """Continuously read inotify events and dispatch to callback."""
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                inotify_fd = self._inotify
                # Read with a 500 ms timeout so stop() can interrupt promptly
                evts = await loop.run_in_executor(
                    None, lambda: inotify_fd.read(timeout=500)
                )
                for event in evts:
                    if event.name and self._running:
                        file_path = self.input_path / event.name
                        if file_path.is_file():
                            try:
                                self.callback(file_path)
                            except Exception:
                                pass
            except asyncio.CancelledError:
                break
            except Exception:
                if not self._running:
                    break
                await asyncio.sleep(0.1)

    async def _process_events(self) -> None:
        """Process a single batch of events — used by unit tests."""
        if not self._running:
            return
        for event in events.read():
            if event.mask & 0x88:  # IN_CLOSE_WRITE or IN_MOVED_TO
                try:
                    if self.callback:
                        self.callback(self.input_path / event.name)
                except Exception:
                    pass

    def register_callback(self, callback: Callable[[Path], None]) -> None:
        self.callback = callback
