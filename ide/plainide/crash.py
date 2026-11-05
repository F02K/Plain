"""Crash reports: written to a file, never raising an error of their own."""

import os
import platform
import time
import traceback

from . import VERSION
from .paths import DATA_DIR, FROZEN, LOG_PATH


def log_crash(where, exc_type, exc, tb):
    """Append a crash report to the log file. Returns True when it was written."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')}  Plain IDE {VERSION}  in {where}\n")
            f.write(f"Python {platform.python_version()}  {platform.platform()}  frozen={FROZEN}\n")
            f.write("".join(traceback.format_exception(exc_type, exc, tb)))
            f.write("\n")
        return True
    except OSError:
        return False
