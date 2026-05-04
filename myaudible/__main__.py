"""Module entry point for myAudible CLI.

This module allows running myAudible as a module:
    python -m myaudible -i input.md -o output
"""

from myaudible.cli import main

if __name__ == '__main__':
    main()
