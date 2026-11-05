"""Starts the IDE (called by ide/plain_ide.py)."""

import json
import sys
import time
import tkinter as tk
from tkinter import messagebox

from . import TITLE
from .app import App
from .crash import log_crash
from .paths import LOG_PATH


def selftest(app, root, report):
    """Run the first tab with 'Live values' on and write what the IDE showed to a file, then quit."""
    root.withdraw()
    app.live_var.set(True)
    app.running.run()
    deadline = time.time() + 15

    def finish():
        tab = app.running.tab
        if app.runner.running and time.time() < deadline:
            root.after(200, finish)
            return
        root.after(600, lambda: write(tab))

    def write(tab):
        data = {"output": app.output.get(), "values": tab.inline if tab else {},
                "labels": len(tab.inline_labels) if tab else 0}
        with open(report, "w", encoding="utf-8") as f:
            json.dump(data, f)
        app.runner.stop()
        root.destroy()

    root.after(200, finish)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        root = tk.Tk()
        root.geometry("1240x800")
        root.minsize(680, 460)
        report = None
        if args[:1] == ["--selftest"]:       # used by the build checks: run the file with live values, hidden
            report, args = args[1], args[2:]
            root.geometry("1100x760+4000+4000")
        app = App(root, args)
        if report:
            root.after(300, lambda: selftest(app, root, report))
        root.mainloop()
    except Exception:
        info = sys.exc_info()
        log_crash("startup", *info)
        try:
            messagebox.showerror(f"{TITLE} - problem", f"The IDE could not start.\n\n{info[1]}\n\nDetails: {LOG_PATH}")
        except Exception:
            pass
        return 1
    return 0
