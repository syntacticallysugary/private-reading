"""Tests for FileWatcher class."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from myaudible.exceptions import MonitoringError, FileWatcherError
from myaudible.core.file_watcher import FileWatcher


class TestFileWatcher:
    """Test cases for FileWatcher."""

    @pytest.fixture
    def file_watcher(self, tmp_dir):
        """Create FileWatcher instance."""
        callback = MagicMock()
        return FileWatcher(
            input_path=tmp_dir,
            callback=callback,
        )

    @pytest.fixture
    def file_watcher_no_inotify(self, tmp_dir):
        """Create FileWatcher instance with inotify unavailable."""
        callback = MagicMock()
        return FileWatcher(
            input_path=tmp_dir,
            callback=callback,
        )

    @pytest.mark.asyncio
    async def test_start_success(self, file_watcher, tmp_dir):
        """Test successful watcher start."""
        # Mock inotify to be available
        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.watch") as mock_watch:
                mock_watch.return_value = None

                await file_watcher.start()

                # Verify watcher is running
                assert file_watcher._running is True

                # Verify watch was called
                mock_watch.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_no_inotify(self, file_watcher_no_inotify):
        """Test start fails when inotify not available."""
        with patch("core.file_watcher.HAS_INOTIFY", False):
            with pytest.raises(FileWatcherError) as exc_info:
                await file_watcher_no_inotify.start()

            assert "inotify-simple not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_success(self, file_watcher, tmp_dir):
        """Test successful watcher stop."""
        # Start watcher first
        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.watch"):
                await file_watcher.start()

        # Stop watcher
        await file_watcher.stop()

        # Verify watcher is stopped
        assert file_watcher._running is False

    @pytest.mark.asyncio
    async def test_stop_without_start(self, file_watcher, tmp_dir):
        """Test stop without prior start."""
        # Don't start, just stop
        await file_watcher.stop()

        # Should not raise error
        assert file_watcher._running is False

    @pytest.mark.asyncio
    async def test_register_callback(self, file_watcher, tmp_dir):
        """Test callback registration."""
        new_callback = MagicMock()

        file_watcher.register_callback(new_callback)

        # Verify callback was set
        assert file_watcher.callback == new_callback

    @pytest.mark.asyncio
    async def test_register_callback_replaces(self, file_watcher, tmp_dir):
        """Test callback registration replaces previous callback."""
        old_callback = MagicMock()
        new_callback = MagicMock()

        file_watcher.register_callback(old_callback)
        file_watcher.register_callback(new_callback)

        # Verify new callback replaced old
        assert file_watcher.callback == new_callback

    @pytest.mark.asyncio
    async def test_process_events_triggers_callback(self, file_watcher, tmp_dir):
        """Test event processing triggers callback."""
        # Mock inotify events
        mock_event = MagicMock()
        mock_event.mask = 0x8  # IN_CLOSE_WRITE
        mock_event.name = "test.txt"

        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[mock_event]):
                await file_watcher.start()

                # Process events
                await file_watcher._process_events()

                # Verify callback was called
                file_watcher.callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_events_no_events(self, file_watcher, tmp_dir):
        """Test event processing with no events."""
        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[]):
                await file_watcher.start()

                # Process events
                await file_watcher._process_events()

                # Should not raise
                assert True

    @pytest.mark.asyncio
    async def test_process_events_callback_error(self, file_watcher, tmp_dir):
        """Test event processing handles callback errors."""
        # Create callback that raises
        def failing_callback(path):
            raise ValueError("Callback failed")

        file_watcher.register_callback(failing_callback)

        # Mock inotify events
        mock_event = MagicMock()
        mock_event.mask = 0x8  # IN_CLOSE_WRITE
        mock_event.name = "test.txt"

        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[mock_event]):
                await file_watcher.start()

                # Process events - should handle error gracefully
                await file_watcher._process_events()

                # Should not raise, error was logged

    @pytest.mark.asyncio
    async def test_process_events_stops_when_not_running(self, file_watcher, tmp_dir):
        """Test event processing stops when watcher is stopped."""
        # Start watcher
        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.watch"):
                await file_watcher.start()

        # Stop watcher
        await file_watcher.stop()

        # Mock inotify events
        mock_event = MagicMock()
        mock_event.mask = 0x8  # IN_CLOSE_WRITE
        mock_event.name = "test.txt"

        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[mock_event]):
                # Should not raise when processing after stop
                await file_watcher._process_events()

    @pytest.mark.asyncio
    async def test_start_creates_watches(self, file_watcher, tmp_dir):
        """Test start creates watches for input path."""
        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.watch") as mock_watch:
                mock_watch.return_value = None

                await file_watcher.start()

                # Verify watch was called for input_path
                mock_watch.assert_called_once_with(file_watcher.input_path, mask=0x88)

                # Verify watch was registered
                assert file_watcher.input_path in file_watcher._watches

    @pytest.mark.asyncio
    async def test_start_handles_exception(self, file_watcher, tmp_dir):
        """Test start handles exceptions gracefully."""
        # Mock watch to raise
        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.watch", side_effect=Exception("Watch failed")):
                with pytest.raises(FileWatcherError):
                    await file_watcher.start()

    @pytest.mark.asyncio
    async def test_register_callback_async(self, file_watcher, tmp_dir):
        """Test callback registration with async callback."""
        async def async_callback(path):
            await asyncio.sleep(0)

        file_watcher.register_callback(async_callback)

        # Verify callback was set
        assert file_watcher.callback == async_callback

    @pytest.mark.asyncio
    async def test_process_events_with_multiple_events(self, file_watcher, tmp_dir):
        """Test event processing with multiple events."""
        # Mock multiple inotify events
        mock_event1 = MagicMock()
        mock_event1.mask = 0x8  # IN_CLOSE_WRITE
        mock_event1.name = "test1.txt"

        mock_event2 = MagicMock()
        mock_event2.mask = 0x8  # IN_CLOSE_WRITE
        mock_event2.name = "test2.txt"

        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[mock_event1, mock_event2]):
                await file_watcher.start()

                # Process events
                await file_watcher._process_events()

                # Verify callback was called for each event
                assert file_watcher.callback.call_count == 2

    @pytest.mark.asyncio
    async def test_process_events_non_close_write_events(self, file_watcher, tmp_dir):
        """Test event processing ignores non CLOSE_WRITE events."""
        # Mock inotify events with different masks
        mock_event1 = MagicMock()
        mock_event1.mask = 0x8  # IN_CLOSE_WRITE
        mock_event1.name = "test1.txt"

        mock_event2 = MagicMock()
        mock_event2.mask = 0x100  # IN_CREATE (should be ignored)
        mock_event2.name = "test2.txt"

        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[mock_event1, mock_event2]):
                await file_watcher.start()

                # Process events
                await file_watcher._process_events()

                # Verify callback was only called for CLOSE_WRITE event
                assert file_watcher.callback.call_count == 1

    @pytest.mark.asyncio
    async def test_file_watcher_initialization(self, tmp_dir):
        """Test FileWatcher initialization."""
        callback = MagicMock()
        watcher = FileWatcher(
            input_path=tmp_dir,
            callback=callback,
        )

        # Verify initialization
        assert watcher.input_path == tmp_dir
        assert watcher.callback == callback
        assert watcher._running is False

    @pytest.mark.asyncio
    async def test_file_watcher_with_callback(self, tmp_dir):
        """Test FileWatcher with actual callback invocation."""
        callback_invocations = []

        def test_callback(path):
            callback_invocations.append(str(path))

        watcher = FileWatcher(
            input_path=tmp_dir,
            callback=test_callback,
        )

        # Create a test file
        test_file = tmp_dir / "test.txt"
        test_file.write_text("test content")

        # Mock inotify events
        mock_event = MagicMock()
        mock_event.mask = 0x8  # IN_CLOSE_WRITE
        mock_event.name = "test.txt"

        with patch("core.file_watcher.HAS_INOTIFY", True):
            with patch("core.file_watcher.events.read", return_value=[mock_event]):
                await watcher.start()

                # Process events
                await watcher._process_events()

                # Verify callback was invoked
                assert len(callback_invocations) == 1
                assert "test.txt" in callback_invocations[0]
