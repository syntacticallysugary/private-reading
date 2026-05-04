"""Application entry point for myAudible.

This module provides the CLI entry point for the myAudible application.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from myaudible.app import App


def main() -> int:
    """Main entry point for myAudible CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    app = App()

    try:
        asyncio.run(app.run())
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
