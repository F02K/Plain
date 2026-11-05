"""Crash handling and recovery: unsaved work is stored every 20 seconds and offered again after a crash."""

import json
import os
import shutil
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from . import TITLE
from .crash import log_crash
from .paths import DATA_DIR, LOG_PATH, RECOVERY_DIR, open_in_file_manager


class Session:
    def __init__(self, app):
        self.app = app
        self.reporting = False

    # ---- crashes ----------------------------------------------------------------

    def install_crash_handler(self):
        root = self.app.root
        root.report_callback_exception = lambda *info: self.report("the window", *info)
        sys.excepthook = lambda *info: self.report("the program", *info)
        if hasattr(threading, "excepthook"):
            threading.excepthook = lambda a: log_crash(f"thread {a.thread.name if a.thread else '?'}",
                                                       a.exc_type, a.exc_value, a.exc_traceback)

    def report(self, where, exc_type, exc, tb):
        """Write the report, save every unsaved tab, and tell the user what happened."""
        if self.reporting:
            return
        self.reporting = True
        try:
            logged = log_crash(where, exc_type, exc, tb)
            saved = self.save_recovery()
            lines = ["Something went wrong inside the IDE."]
            lines.append("Your unsaved work was saved and will be offered again when you restart."
                         if saved else "I could not save a recovery copy of your work.")
            lines.append(f"Details: {LOG_PATH}" if logged else "I could not write the crash log.")
            lines.append(f"\n{exc_type.__name__}: {exc}")
            lines.append("\nKeep working? (No closes the IDE.)")
            try:
                keep = messagebox.askyesno(f"{TITLE} - problem", "\n".join(lines), icon="warning")
            except tk.TclError:
                keep = False
            if not keep:
                self.app.root.destroy()
        finally:
            self.reporting = False

    # ---- recovery ---------------------------------------------------------------

    def save_recovery(self):
        """Store all unsaved tabs. Returns True if something was saved."""
        try:
            dirty = self.app.documents.modified()
            shutil.rmtree(RECOVERY_DIR, ignore_errors=True)
            if not dirty:
                return False
            os.makedirs(RECOVERY_DIR, exist_ok=True)
            index = []
            for n, tab in enumerate(dirty):
                name = f"tab{n}.plain"
                with open(os.path.join(RECOVERY_DIR, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write(tab.source())
                index.append({"file": name, "path": tab.path})
            with open(os.path.join(RECOVERY_DIR, "session.json"), "w", encoding="utf-8") as f:
                json.dump(index, f)
            return True
        except (OSError, tk.TclError):
            return False

    def autosave(self):
        self.save_recovery()
        self.app.root.after(20000, self.autosave)

    def restore(self):
        """Offer to bring back the unsaved work of a session that did not end normally."""
        index_path = os.path.join(RECOVERY_DIR, "session.json")
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
            items = []
            for entry in index:
                with open(os.path.join(RECOVERY_DIR, entry["file"]), encoding="utf-8") as f:
                    items.append((entry.get("path"), f.read()))
        except (OSError, ValueError, KeyError):
            return False
        if not items:
            return False
        if not messagebox.askyesno(TITLE, f"The IDE did not close normally last time.\n"
                                          f"Bring back {len(items)} unsaved tab(s)?"):
            shutil.rmtree(RECOVERY_DIR, ignore_errors=True)
            return False
        for path, content in items:
            tab = self.app.documents.new(path, content)
            tab.dirty = True
        self.app.documents.refresh()
        return True

    def clear_recovery(self):
        shutil.rmtree(RECOVERY_DIR, ignore_errors=True)

    def open_data_folder(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        open_in_file_manager(DATA_DIR)
