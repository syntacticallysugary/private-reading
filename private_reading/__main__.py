"""Module entry point for Private Reading CLI.

This module allows running Private Reading as a module:
    python -m private_reading -i input.md -o output
"""

from private_reading.cli import main

if __name__ == '__main__':
    main()
