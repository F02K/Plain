"""Settings that are remembered between sessions (theme, sidebar, ...)."""

import json
import os

from .paths import DATA_DIR, SETTINGS_PATH


def load():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(**changes):
    """Change some settings and keep the others."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(dict(load(), **changes), f)
    except OSError:
        pass
