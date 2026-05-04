"""Async application class for myAudible.

This module provides the main application class that orchestrates
the file processing pipeline.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from myaudible.config import AppConfig
from myaudible.utils.logging import setup_logging, get_logger


class App:
    """Async application class for myAudible.

    This class orchestrates the file processing pipeline by:
    1. Loading configuration
    2. Setting up logging
    3. Starting the file watcher
    4. Processing files as they arrive
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize application.

        Args:
            config: Optional configuration override.
        """
        self.config = config or AppConfig()
        self.logger = get_logger()
        self._running = False

    async def run(self) -> None:
        """Run the application."""
        await self._setup()
        self._running = True

        try:
            await self._process_files()
        finally:
            await self._cleanup()

    async def _setup(self) -> None:
        """Set up application components."""
        setup_logging(self.config)
        self.logger.info("Application started", config=self.config)

    async def _process_files(self) -> None:
        """Process files from input directory."""
        raise NotImplementedError("File processing not implemented yet")

    async def _cleanup(self) -> None:
        """Clean up resources."""
        self._running = False
        self.logger.info("Application stopped")
