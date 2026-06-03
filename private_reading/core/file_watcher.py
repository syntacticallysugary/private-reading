"""File monitoring for Private Reading — re-exports from top-level core."""
from core.file_watcher import (  # noqa: F401
    HAS_INOTIFY,
    FileWatcherError,
    FileWatcher,
    events,
    watch,
)
