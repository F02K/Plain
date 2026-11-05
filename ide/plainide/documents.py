"""The open files: tabs, saving, closing, and what happens when a file is renamed or deleted."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import TITLE
from .editor import EditorTab
from .language import NEW_PROGRAM
from .projects import EXT
from .tabstrip import TabStrip


def same_path(a, b):
    return bool(a) and bool(b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


class Documents:
    def __init__(self, app, parent):
        self.app = app
        self.list = []
        self.selected = None
        self.untitled_count = 0
        self.menu_doc = None
        self.strip = TabStrip(parent, app, self.select, self.close, self.show_menu)
        self.stack = ttk.Frame(parent)
        self.stack.rowconfigure(0, weight=1)
        self.stack.columnconfigure(0, weight=1)
        self.menu = tk.Menu(app.root, tearoff=False)
        self.menu.add_command(label="Close", command=lambda: self.close(self.menu_doc))
        self.menu.add_command(label="Close others", command=self.close_others)
        self.menu.add_command(label="Close all", command=self.close_all)
        self.menu.add_separator()
        self.menu.add_command(label="Copy path", command=self.copy_menu_path)
        self.menu.add_command(label="Show in Explorer", command=self.reveal_menu_doc)

    # ---- the list of tabs ------------------------------------------------------

    def tabs(self):
        return list(self.list)

    def current(self):
        return self.selected

    def new(self, path=None, content=NEW_PROGRAM):
        untitled = None
        if path is None:
            self.untitled_count += 1
            untitled = f"Untitled {self.untitled_count}"
        doc = EditorTab(self.app, self.stack, path, content, untitled)
        doc.grid(row=0, column=0, sticky="nsew")
        self.list.append(doc)
        self.strip.add(doc)
        self.select(doc)
        return doc

    def select(self, doc):
        if doc not in self.list:
            return
        for other in self.list:
            other.completer.hide()
        self.selected = doc
        doc.tkraise()
        self.strip.select(doc)
        doc.text.focus_set()
        self.refresh()
        doc.update_cursor()

    def next(self, step=1):
        if len(self.list) > 1:
            self.select(self.list[(self.list.index(self.selected) + step) % len(self.list)])

    def refresh(self, _doc=None):
        """Titles of the tabs, the window title and the status bar."""
        for doc in self.list:
            self.strip.update(doc)
        self.app.update_titles()

    def find(self, path):
        for doc in self.list:
            if same_path(doc.path, path):
                return doc
        return None

    def modified(self):
        return [doc for doc in self.list if doc.dirty]

    # ---- opening ---------------------------------------------------------------

    def open_path(self, path):
        existing = self.find(path)
        if existing:
            self.select(existing)
            return existing
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            messagebox.showinfo(TITLE, "This file is not a text file, so I cannot open it here.")
            return None
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot open this file: {exc.strerror}")
            return None
        # Replace an untouched empty starter tab instead of keeping it around.
        starter = self.list[0] if len(self.list) == 1 else None
        doc = self.new(os.path.abspath(path), content)
        if starter and starter.path is None and not starter.dirty and starter.source() == NEW_PROGRAM:
            self.close(starter)
        return doc

    def open_dialog(self):
        for path in filedialog.askopenfilenames(filetypes=[("Plain programs", "*.plain"), ("Plain projects", "*" + EXT),
                                                           ("All files", "*.*")]):
            self.app.open_any(path)

    def open_example(self, path):
        with open(path, encoding="utf-8") as f:
            self.new(None, f.read())

    # ---- saving ----------------------------------------------------------------

    def confirm_save(self, doc):
        """Ask what to do with unsaved changes. Returns False when the user cancels."""
        if not doc.dirty:
            return True
        self.select(doc)
        answer = messagebox.askyesnocancel(TITLE, f"Save '{doc.name}' before closing?")
        if answer is None:
            return False
        return self.save(doc) if answer else True

    def save(self, doc=None):
        doc = doc or self.selected
        if doc is None:
            return False
        if doc.path is None:
            return self.save_as(doc)
        return self.write(doc, doc.path)

    def save_as(self, doc=None):
        doc = doc or self.selected
        if doc is None:
            return False
        if doc.path is None and self.app.projects.folder is None:
            # A first save always creates a project, so the program has a home for its builds.
            return self.app.projects.new_dialog(doc)
        options = {"defaultextension": ".plain", "filetypes": [("Plain programs", "*.plain"), ("All files", "*.*")]}
        if self.app.projects.folder:
            options["initialdir"] = self.app.projects.folder
        path = filedialog.asksaveasfilename(**options)
        return bool(path) and self.write(doc, path)

    def save_all(self):
        for doc in self.list:
            if doc.dirty and not self.save(doc):
                break

    def write(self, doc, path):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                source = doc.source()
                f.write(source if not source or source.endswith("\n") else source + "\n")
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot save this file: {exc.strerror}")
            return False
        doc.path = os.path.abspath(path)
        doc.untitled = None
        doc.dirty = False
        doc.rehighlight()
        self.refresh()
        self.app.explorer.refresh()
        self.app.projects.file_saved(doc.path)
        return True

    # ---- closing ---------------------------------------------------------------

    def close(self, doc=None):
        doc = doc or self.selected
        if doc is None or not self.confirm_save(doc):
            return False
        index = self.list.index(doc)
        doc.completer.hide()
        self.list.remove(doc)
        self.strip.remove(doc)
        doc.destroy()
        if self.app.running.tab is doc:
            self.app.running.tab = None
        if not self.list:
            self.new()
        elif self.selected is doc:
            self.select(self.list[min(index, len(self.list) - 1)])
        self.refresh()
        return True

    def close_others(self):
        for doc in self.tabs():
            if doc is not self.menu_doc and not self.close(doc):
                break

    def close_all(self):
        for doc in self.tabs():
            if not self.close(doc):
                break

    # ---- the tab menu ----------------------------------------------------------

    def show_menu(self, doc, event):
        from .theme import style_menu
        style_menu(self.menu, self.app.theme)
        self.menu_doc = doc
        has_path = bool(doc.path)
        self.menu.entryconfig("Copy path", state="normal" if has_path else "disabled")
        self.menu.entryconfig("Show in Explorer", state="normal" if has_path else "disabled")
        self.menu.tk_popup(event.x_root, event.y_root)

    def copy_menu_path(self):
        if self.menu_doc and self.menu_doc.path:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(self.menu_doc.path)

    def reveal_menu_doc(self):
        from .paths import open_in_file_manager
        if self.menu_doc and self.menu_doc.path:
            open_in_file_manager(self.menu_doc.path)

    # ---- files changed in the Explorer -----------------------------------------

    def path_renamed(self, old, new):
        """A file or folder was renamed: tabs that belong to it follow."""
        for doc in self.list:
            if not doc.path:
                continue
            if same_path(doc.path, old):
                doc.path = new
            elif os.path.normcase(os.path.abspath(doc.path)).startswith(os.path.normcase(os.path.abspath(old)) + os.sep):
                doc.path = os.path.join(new, os.path.relpath(doc.path, old))
            else:
                continue
            doc.rehighlight()
        self.refresh()

    def path_removed(self, path):
        """A file or folder was deleted: its tabs stay open as unsaved text, so nothing is lost."""
        base = os.path.normcase(os.path.abspath(path))
        for doc in self.list:
            if doc.path and (os.path.normcase(os.path.abspath(doc.path)) == base
                             or os.path.normcase(os.path.abspath(doc.path)).startswith(base + os.sep)):
                doc.untitled = os.path.basename(doc.path)
                doc.path = None
                doc.dirty = True
                doc.rehighlight()
        self.refresh()
