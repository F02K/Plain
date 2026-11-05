"""Go to file (Ctrl+P): type a few letters of a file name and press Enter, like in Visual Studio Code."""

import os
import tkinter as tk

MAX_SHOWN = 12
WIDTH = 520


def matches(query, text):
    """True when the letters of the query appear in the text in this order (so 'bg' finds 'ball_game')."""
    pos = 0
    text = text.lower()
    for ch in query.lower():
        pos = text.find(ch, pos)
        if pos < 0:
            return False
        pos += 1
    return True


def rank(query, relative):
    """Smaller is better: names that start with the query first, then names that contain it."""
    name = os.path.basename(relative).lower()
    q = query.lower()
    return (0 if name.startswith(q) else 1 if q in name else 2 if q in relative.lower() else 3, len(relative), relative)


def project_files(app):
    """Relative paths of the files in the project folder, plus the open files that are somewhere else."""
    root = app.projects.folder
    found = {}
    if root:
        for _parent, name, path, is_dir, _depth in app.explorer.walk(root):
            if not is_dir:
                found[os.path.normcase(path)] = (os.path.relpath(path, root).replace("\\", "/"), path)
    for doc in app.documents.tabs():
        if doc.path and os.path.normcase(os.path.abspath(doc.path)) not in found:
            found[os.path.normcase(os.path.abspath(doc.path))] = (doc.path, doc.path)
    return sorted(found.values())


class QuickOpen:
    def __init__(self, app):
        self.app = app
        t = app.theme
        self.files = project_files(app)
        self.shown = []
        self.armed = False          # the window only closes on losing the focus after it had the focus once
        root = app.root
        self.win = tk.Toplevel(root)
        self.win.wm_overrideredirect(True)
        self.win.configure(bg=t["accent"])
        self.x = root.winfo_rootx() + (root.winfo_width() - WIDTH) // 2
        self.y = root.winfo_rooty() + 70
        box = tk.Frame(self.win, bg=t["pop_bg"])
        box.pack(fill="both", expand=True, padx=1, pady=1)
        self.var = tk.StringVar()
        self.entry = tk.Entry(box, textvariable=self.var, font=app.ui_font, bd=0, relief="flat",
                              bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"])
        self.entry.pack(fill="x", padx=6, pady=6, ipady=3)
        self.list = tk.Listbox(box, font=app.ui_font, bd=0, highlightthickness=0, activestyle="none",
                               bg=t["pop_bg"], fg=t["fg"], selectbackground=t["pop_sel"], selectforeground=t["fg"],
                               exportselection=False)
        self.list.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.var.trace_add("write", lambda *_: self.update())
        self.entry.bind("<Return>", lambda e: self.accept())
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Up>", lambda e: self.move(-1))
        self.entry.bind("<Down>", lambda e: self.move(1))
        self.entry.bind("<FocusIn>", lambda e: setattr(self, "armed", True))
        self.entry.bind("<FocusOut>", lambda e: self.win.after(120, self.close_if_unfocused))
        self.list.bind("<ButtonRelease-1>", lambda e: self.accept())
        self.update()
        self.win.update_idletasks()
        self.entry.focus_force()

    def update(self):
        query = self.var.get().strip()
        pool = [item for item in self.files if not query or matches(query, item[0])]
        pool.sort(key=lambda item: rank(query, item[0]) if query else (0, 0, item[0]))
        self.shown = pool[:MAX_SHOWN]
        self.list.delete(0, "end")
        for relative, _path in self.shown:
            self.list.insert("end", relative)
        if self.shown:
            self.list.selection_set(0)
        rows = max(1, len(self.shown))
        self.win.wm_geometry(f"{WIDTH}x{52 + rows * 22}+{self.x}+{self.y}")

    def move(self, delta):
        if not self.shown:
            return "break"
        current = self.list.curselection()[0] if self.list.curselection() else 0
        new = max(0, min(len(self.shown) - 1, current + delta))
        self.list.selection_clear(0, "end")
        self.list.selection_set(new)
        self.list.see(new)
        return "break"

    def accept(self):
        selection = self.list.curselection()
        if not selection:
            return
        path = self.shown[selection[0]][1]
        self.close()
        self.app.open_any(path)

    def close_if_unfocused(self):
        try:
            if self.armed and self.win.winfo_exists() and self.win.focus_displayof() is None:
                self.close()
        except tk.TclError:
            pass

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()
        self.app.quick = None
