"""Entry point used to build the stand-alone `plain` program with PyInstaller."""

import sys

from plain.cli import main

if __name__ == "__main__":
    sys.exit(main())
