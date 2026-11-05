"""Run (F5): translate the program in the current tab and run it in its own process, with live values."""

import json
import os
import re
import queue
import time

from plain.errors import PlainError, format_error
from plain.toolchain import compile_to_python

from .runner import child_command


class RunController:
    def __init__(self, app):
        self.app = app
        self.id = 0
        self.tab = None             # the tab that was run last
        self.watch_file = None
        self.watch_seq = 0

    @property
    def runner(self):
        return self.app.runner

    # ---- starting and stopping -------------------------------------------------

    def run(self):
        app = self.app
        tab = app.documents.current()
        if tab is None:
            return
        if tab.kind != "plain":
            app.output.clear()
            app.output.write(f"'{tab.name}' is not a Plain program, so there is nothing to run.\n", "info")
            return
        self.runner.stop()
        self.id += 1
        run_id = self.id
        source = tab.source()
        self.tab = tab
        for t in app.documents.tabs():
            t.clear_marks()
        app.output.clear()
        self.reset_watch()
        watch = app.watch_var.get() or app.live_var.get()
        for t in app.documents.tabs():
            t.clear_inline()
        try:
            py_path = os.path.join(app.tmp, f"program{run_id}.py")
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(compile_to_python(source, watch=watch, base_dir=self.base_dir_of(tab)))
        except PlainError as err:
            self.show_compile_error(tab, source, err)
            return
        extra_env = None
        if watch:
            self.watch_file = os.path.join(app.tmp, f"watch{run_id}.json")
            extra_env = {"PLAIN_WATCH": self.watch_file}
        self.start(child_command() + [py_path], extra_env)

    def base_dir_of(self, tab):
        """Where 'import name' looks for files: next to the program, or in the project folder."""
        if tab.path:
            return os.path.dirname(os.path.abspath(tab.path))
        return self.app.projects.folder

    def show_compile_error(self, tab, source, err):
        self.app.output.clear()
        self.set_running(False)
        self.app.output.write(format_error(err, source, tab.name) + "\n", "err")
        if err.file:                    # the mistake is in an imported file: open it there
            other = self.app.documents.open_path(err.file)
            if other is not None:
                other.mark_line(err.line)
        else:
            tab.mark_line(err.line)

    def start(self, cmd, extra_env=None):
        self.app.output.clear()
        try:
            self.runner.start(cmd, extra_env)
        except OSError as exc:
            self.set_running(False)
            self.app.output.write(f"I could not start the program: {exc}\n", "err")
            return
        self.set_running(True)

    def stop(self):
        if self.runner.running:
            self.runner.stop()
            self.app.output.write("\n[stopped]\n", "info")

    def set_running(self, running):
        app = self.app
        app.toolbar.run_button.config(state="disabled" if running else "normal")
        app.toolbar.stop_button.config(state="normal" if running else "disabled")
        app.output.allow_input(running)
        app.status.set("Running..." if running else "Ready", running)
        if not running and app.documents.current():
            app.documents.current().text.focus_set()

    def send_input(self, line):
        if not self.runner.running:
            return
        self.app.output.write(line + "\n", "in")
        self.runner.send(line)

    # ---- what the program prints -----------------------------------------------

    def poll(self):
        app = self.app
        app.building.handle_events()
        try:
            while True:
                proc, kind, data = self.runner.events.get_nowait()
                if proc is not self.runner.proc:
                    continue
                if kind == "out":
                    for piece in data.splitlines(keepends=True):
                        failed = piece.startswith(("Error in line", "Error:"))
                        app.output.write(piece, "err" if failed else None)
                        m = re.match(r"Error in line (\d+):", piece)
                        if m and self.tab:
                            self.tab.mark_line(int(m.group(1)))
                else:
                    self.set_running(False)
                    if data not in (0, None):
                        app.output.write(f"\n[program ended with code {data}]\n", "info")
        except queue.Empty:
            pass
        app.root.after(40, self.poll)

    # ---- the values behind the code ------------------------------------------------

    def reset_watch(self):
        self.watch_file = None
        self.watch_seq = 0
        self.app.values.reset()

    def poll_watch(self):
        app = self.app
        try:
            if (app.watch_var.get() or app.live_var.get()) and self.watch_file and os.path.exists(self.watch_file):
                with open(self.watch_file, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("seq") != self.watch_seq:
                    self.watch_seq = data["seq"]
                    if app.watch_var.get():
                        app.values.update_rows(data["vars"])
                    tab = self.tab
                    if app.live_var.get() and tab in app.documents.tabs():
                        tab.set_inline({int(n): text for n, text in data.get("lines", {}).items()})
            app.values.fade()
        except (OSError, ValueError, KeyError, TypeError):
            pass
        app.root.after(200, self.poll_watch)

    def show_value(self, name, line):
        """A row of the value list was clicked: jump to the code."""
        tab = self.tab if self.tab in self.app.documents.tabs() else self.app.documents.current()
        if tab is not None:
            self.app.documents.select(tab)
            tab.show_name(name, line)
