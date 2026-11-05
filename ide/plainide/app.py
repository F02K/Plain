"""The application: builds the window and connects the parts (see the list in __init__.py)."""

import os
import shutil
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk

from . import TITLE, settings
from .activitybar import ActivityBar
from .building import BuildController
from .dialogs import help_window
from .documents import Documents
from .explorer import Explorer
from .icons import Icons
from .menus import build_menu
from .output import OutputPanel
from .paths import ROOT
from .projects import EXT
from .projectui import ProjectController
from .quickopen import QuickOpen
from .runner import Runner
from .running import RunController
from .session import Session
from .statusbar import StatusBar
from .theme import THEMES, apply_styles, make_fonts
from .toolbar import Toolbar
from .values import ValuesPanel

SIDEBAR_WIDTH = 250


class App:
    def __init__(self, root, paths=()):
        self.root = root
        self.theme_name = settings.load().get("theme", "Dark")
        if self.theme_name not in THEMES:
            self.theme_name = "Dark"
        self.theme = THEMES[self.theme_name]
        self.runner = Runner()
        self.tmp = tempfile.mkdtemp(prefix="plain_ide_")
        self.view = None                                   # "explorer", "values" or None (sidebar hidden)
        self.quick = None
        self.watch_var = tk.BooleanVar(value=False)        # the list of values (the Values view)
        self.live_var = tk.BooleanVar(value=False)         # the values behind the code
        self.font, self.small_font, self.ui_bold, self.ui_font = make_fonts(root)
        apply_styles(root, self.theme, self.ui_font)
        self.icons = Icons(self.theme, self.root)

        # the parts that do the work
        self.status = StatusBar(root)
        self.projects = ProjectController(self)
        self.running = RunController(self)
        self.building = BuildController(self)
        self.session = Session(self)
        self.toolbar = Toolbar(root, self)
        self.toolbar.pack(side="top", fill="x")
        self.status.pack(side="bottom", fill="x")
        self.build_layout()
        root.config(menu=build_menu(self))
        self.bind_keys()
        self.session.install_crash_handler()

        self.session.restore()
        for path in paths:
            self.open_any(path)
        if not self.documents.tabs():
            self.documents.new()
        self.documents.refresh()
        self.show_view("explorer")
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.after(40, self.running.poll)
        root.after(200, self.running.poll_watch)
        root.after(20000, self.session.autosave)

    # ---- layout ------------------------------------------------------------------

    def build_layout(self):
        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True)
        self.activity = ActivityBar(body, self, self.pick_view)
        self.activity.pack(side="left", fill="y")
        self.hpane = ttk.PanedWindow(body, orient="horizontal")
        self.hpane.pack(side="left", fill="both", expand=True)

        self.sidebar = ttk.Frame(self.hpane, style="Side.TFrame", width=SIDEBAR_WIDTH)
        self.sidebar.rowconfigure(0, weight=1)
        self.sidebar.columnconfigure(0, weight=1)

        main = ttk.Frame(self.hpane)
        self.hpane.add(main, weight=1)
        vpane = ttk.PanedWindow(main, orient="vertical")
        vpane.pack(fill="both", expand=True)
        editor_area = ttk.Frame(vpane)
        editor_area.rowconfigure(1, weight=1)
        editor_area.columnconfigure(0, weight=1)
        self.documents = Documents(self, editor_area)
        self.documents.strip.grid(row=0, column=0, sticky="ew")
        self.documents.stack.grid(row=1, column=0, sticky="nsew")
        vpane.add(editor_area, weight=3)
        self.output = OutputPanel(vpane, self, self.running.send_input)
        vpane.add(self.output, weight=1)

        self.explorer = Explorer(self.sidebar, self)
        self.values = ValuesPanel(self.sidebar, self, self.running.show_value)
        self.explorer.grid(row=0, column=0, sticky="nsew")
        self.values.grid(row=0, column=0, sticky="nsew")

    def bind_keys(self):
        for sequence, action in self.shortcuts():
            self.root.bind(sequence, lambda e, a=action: a())

    def bind_shortcuts(self, widget):
        """The text widget has its own Ctrl keys (Ctrl+O opens a new line...), so route ours through it."""
        for sequence, action in self.shortcuts():
            widget.bind(sequence, lambda e, a=action: (a(), "break")[1])

    def shortcuts(self):
        d = self.documents
        return [
            ("<F5>", self.running.run), ("<Shift-F5>", self.running.stop),
            ("<F6>", self.building.build), ("<F7>", self.building.release), ("<F1>", self.show_help),
            ("<Control-n>", lambda: d.new()), ("<Control-o>", d.open_dialog),
            ("<Control-s>", d.save), ("<Control-S>", d.save_as), ("<Control-w>", d.close),
            ("<Control-Tab>", d.next), ("<Control-Shift-Tab>", lambda: d.next(-1)),
            ("<Control-p>", self.quick_open), ("<Control-b>", self.toggle_sidebar),
            ("<Control-E>", self.focus_explorer),
            ("<Control-plus>", lambda: self.zoom(1)), ("<Control-equal>", lambda: self.zoom(1)),
            ("<Control-minus>", lambda: self.zoom(-1)),
        ]

    # ---- the sidebar: Explorer and Values ----------------------------------------------

    def sidebar_visible(self):
        return str(self.sidebar) in self.hpane.panes()

    def show_view(self, name):
        (self.explorer if name == "explorer" else self.values).tkraise()
        if not self.sidebar_visible():
            self.hpane.insert(0, self.sidebar, weight=0)
            self.root.after(30, lambda: self.hpane.sashpos(0, settings.load().get("sidebar_width", SIDEBAR_WIDTH)))
        self.view = name
        self.watch_var.set(name == "values")
        self.activity.set_active(name)

    def hide_sidebar(self):
        if self.sidebar_visible():
            settings.save(sidebar_width=self.hpane.sashpos(0))
            self.hpane.forget(self.sidebar)
        self.view = None
        self.watch_var.set(False)
        self.activity.set_active(None)

    def pick_view(self, name):
        """A click on a button of the activity bar: show the view, or hide the sidebar when it is already shown."""
        if self.view == name:
            self.hide_sidebar()
        else:
            self.show_view(name)
        if name == "values":
            self.running.reset_watch() if not self.watch_var.get() else None

    def toggle_sidebar(self):
        if self.sidebar_visible():
            self.hide_sidebar()
        else:
            self.show_view("explorer")

    def toggle_values(self):
        """The 'Value list' switch in the toolbar and in the View menu."""
        self.show_view("values" if self.watch_var.get() else "explorer")
        self.running.reset_watch()

    def focus_explorer(self):
        self.show_view("explorer")
        self.explorer.tree.focus_set()
        if not self.explorer.tree.selection() and self.explorer.tree.get_children():
            self.explorer.tree.selection_set(self.explorer.tree.get_children()[0])

    def quick_open(self):
        if self.quick is not None:
            self.quick.close()
        self.quick = QuickOpen(self)

    # ---- titles and status ---------------------------------------------------------------

    def update_titles(self):
        doc = self.documents.current()
        info, folder = self.projects.info, self.projects.folder
        project = info.name if info else os.path.basename(folder) if folder else ""
        parts = [f"{'*' if doc.dirty else ''}{doc.name}" if doc else None, project or None, TITLE]
        self.root.title(" - ".join(p for p in parts if p))
        if info:
            self.status.set_project(f"Project: {info.name}")
        elif folder:
            self.status.set_project(f"Folder: {os.path.basename(folder) or folder}")
        else:
            self.status.set_project("")
        if doc:
            self.status.set_language({"plain": "Plain", "project": "Plain project", "text": "Text"}[doc.kind])

    def update_position(self, line, col):
        self.status.set_position(line, col)

    def open_any(self, path):
        """A file from the command line, the Open dialog or Go to file: a project file opens the project."""
        if path.endswith(EXT) and os.path.dirname(os.path.abspath(path)) != self.projects.folder:
            return self.projects.open_info_file(path)
        return self.documents.open_path(path)

    # ---- look ----------------------------------------------------------------------------------

    def toggle_theme(self):
        self.apply_theme("Light" if self.theme_name == "Dark" else "Dark")

    def apply_theme(self, name):
        self.theme_name = name
        self.theme = THEMES[name]
        self.theme_var.set(name)
        settings.save(theme=name)
        apply_styles(self.root, self.theme, self.ui_font)
        self.icons = Icons(self.theme, self.root)
        self.output.restyle(self.theme)
        self.values.restyle(self.theme)
        self.activity.restyle()
        self.documents.strip.restyle()
        self.explorer.restyle()
        for tab in self.documents.tabs():
            tab.restyle()
        self.status.refresh_style()

    def zoom(self, delta):
        self.font.configure(size=max(8, min(36, self.font.cget("size") + delta)))
        self.small_font.configure(size=max(7, self.font.cget("size") - 3))
        self.root.after(50, lambda: [tab.refresh_inline() for tab in self.documents.tabs()])

    def show_help(self):
        help_window(self)

    # ---- leaving ---------------------------------------------------------------------------------

    def quit(self):
        for doc in self.documents.tabs():
            if not self.documents.confirm_save(doc):
                return
        self.shutdown()

    def shutdown(self):
        """Close the window without asking: stop the program, remove temporary files, stop all timers."""
        if self.sidebar_visible():
            settings.save(sidebar_width=self.hpane.sashpos(0))
        self.runner.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.session.clear_recovery()
        for timer in self.root.tk.call("after", "info"):      # no timer may fire on a window that is gone
            self.root.after_cancel(timer)
        self.root.destroy()
