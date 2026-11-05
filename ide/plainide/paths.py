"""Where things are: the program folders, and the folder for settings and crash reports."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the ide/ folder
FROZEN = getattr(sys, "frozen", False)
ROOT = getattr(sys, "_MEIPASS", None) if FROZEN else os.path.dirname(HERE)
LAUNCHER = os.path.join(HERE, "plain_ide.py")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share"), "PlainIDE")
LOG_PATH = os.path.join(DATA_DIR, "crash.log")
RECOVERY_DIR = os.path.join(DATA_DIR, "recovery")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


def open_in_file_manager(path):
    """Show a folder (or the folder of a file) in the file manager of the computer."""
    try:
        if sys.platform.startswith("win"):
            if os.path.isfile(path):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path] if os.path.isfile(path) else ["open", path])
        else:
            subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path)])
    except OSError:
        pass
