"""Build (F6) makes a Python file of the project, Release (F7) makes a program from it."""

import os
import queue
import subprocess
import threading
from tkinter import messagebox

from plain.errors import PlainError, format_error

from . import TITLE
from . import projects as PROJECTS
from .paths import NO_WINDOW, open_in_file_manager


class BuildController:
    def __init__(self, app):
        self.app = app
        self.queue = queue.Queue()
        self.busy = False
        self.log = []

    # ---- build ------------------------------------------------------------------

    def need_project(self):
        app = self.app
        if self.busy:
            return None
        if app.projects.info is None and not app.projects.make_here():
            return None
        info = app.projects.info
        if info is None:
            return None
        doc = app.documents.current()
        if doc is not None and doc.path is None and not info.plain_files():
            app.documents.save(doc)
        for tab in app.documents.tabs():       # build what is on the screen, so save first
            if tab.dirty and tab.path and not app.documents.save(tab):
                return None
        if not os.path.isfile(info.main_path):
            messagebox.showerror(TITLE, f"The main program '{info.main}' does not exist.\n\n"
                                        "Choose another one: right click a program in the Explorer > Set as main "
                                        "program.")
            return None
        return info

    def build(self):
        """Translate the main program to a Python file. Returns the modules it uses, or None on a mistake."""
        app = self.app
        info = self.need_project()
        if info is None:
            return None
        app.output.clear()
        for tab in app.documents.tabs():
            tab.clear_marks()
        try:
            path, imports = PROJECTS.build_python(info)
        except PlainError as err:
            with open(info.main_path, encoding="utf-8") as f:
                source = f.read()
            app.output.write(format_error(err, source, info.main) + "\n", "err")
            tab = app.documents.find(info.main_path)
            if tab:
                tab.mark_line(err.line)
            return None
        except OSError as exc:
            app.output.write(f"I cannot build the program: {exc.strerror}\n", "err")
            return None
        relative = os.path.relpath(path, info.folder)
        app.output.write(f"Built {relative}\nRun it anywhere with Python 3.10 or newer:  python {relative}\n", "info")
        app.explorer.refresh()
        return imports

    # ---- release ----------------------------------------------------------------

    def release(self):
        app = self.app
        imports = self.build()
        if imports is None:
            return
        info = app.projects.info
        app.output.write("\nMaking the program (an exe needs Python and PyInstaller on this computer)...\n", "info")
        app.root.config(cursor="watch")
        app.root.update_idletasks()
        try:
            python, has_pyinstaller = PROJECTS.find_python()
        finally:
            app.root.config(cursor="")
        if python is None:
            app.output.write("I could not find Python 3.10 or newer on this computer.\n"
                             "Install it from python.org, then try Release again. "
                             "The Python file from Build works without this step.\n", "err")
            return
        steps = []
        if not has_pyinstaller:
            if not messagebox.askyesno(TITLE, "To make a program I need PyInstaller.\n\n"
                                              "Install it now? (pip install pyinstaller)"):
                app.output.write("Stopped: PyInstaller is not installed.\n", "err")
                return
            steps.append(python + ["-m", "pip", "install", "pyinstaller"])
        steps.append(python + PROJECTS.pyinstaller_arguments(info, "window" in imports))
        self.set_busy(True)
        self.log = []
        app.output.write("Working... this takes a minute.\n", "info")
        threading.Thread(target=self.run_steps, args=(steps,), daemon=True).start()

    def run_steps(self, steps):
        """Runs in a thread: the output is passed on through the queue."""
        for command in steps:
            try:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=NO_WINDOW)
                for raw in proc.stdout:
                    self.queue.put(("line", raw.decode("utf-8", "replace").rstrip()))
                code = proc.wait()
            except OSError as exc:
                self.queue.put(("line", str(exc)))
                code = 1
            if code != 0:
                self.queue.put(("done", code))
                return
        self.queue.put(("done", 0))

    def set_busy(self, busy):
        self.busy = busy
        self.app.status.set("Building..." if busy else "Ready", busy)
        state = "disabled" if busy else "normal"
        for button in (self.app.toolbar.build_button, self.app.toolbar.release_button):
            button.config(state=state)

    def handle_events(self):
        app = self.app
        try:
            while True:
                kind, data = self.queue.get_nowait()
                if kind == "line":
                    self.log.append(data)
                    continue
                self.set_busy(False)
                info = app.projects.info
                if data == 0 and info and os.path.isfile(info.program_path):
                    app.output.write(f"Done: {os.path.relpath(info.program_path, info.folder)}\n"
                                     "You can give this program to anyone; it needs no Python.\n", "info")
                else:
                    app.output.write("The program could not be made. The last lines of the report:\n", "err")
                    app.output.write("\n".join(self.log[-20:]) + "\n", "err")
                app.explorer.refresh()
        except queue.Empty:
            pass

    def show_folder(self):
        info = self.app.projects.info
        if info is None:
            return
        for folder in (info.dist_dir, info.build_dir, info.folder):
            if os.path.isdir(folder):
                open_in_file_manager(folder)
                return
