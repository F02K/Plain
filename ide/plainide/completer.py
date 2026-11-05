"""The suggestion list that appears while you type (keywords, helpers and the names of the program)."""

import tkinter as tk

from plain.lexer import KEYWORDS

from .language import HELPER_CALLS, HELPERS, OF_HELPERS, SNIPPETS, WORD_BEFORE_CURSOR
from .symbols import TOKEN


class Completer:
    """The suggestion list that appears while you type."""

    def __init__(self, tab):
        self.tab = tab
        self.win = None
        self.box = None
        self.matches = []
        self.prefix = ""

    @property
    def visible(self):
        return self.win is not None

    def prefix_at_cursor(self):
        before = self.tab.text.get("insert linestart", "insert")
        m = WORD_BEFORE_CURSOR.search(before)
        return m.group() if m else ""

    def candidates(self, prefix):
        words = set(KEYWORDS) | HELPERS | set(SNIPPETS)
        for m in TOKEN.finditer(self.tab.text.get("1.0", "end-1c")):
            if m.lastgroup == "word":
                words.add(m.group())
        low = prefix.lower()
        found = [w for w in words if w.lower().startswith(low) and w != prefix]
        found.sort(key=lambda w: (w not in KEYWORDS and w not in HELPERS and w not in SNIPPETS, w.lower()))
        return found[:12]

    def update(self, force=False):
        prefix = self.prefix_at_cursor()
        if len(prefix) < (1 if force else 2):
            self.hide()
            return
        matches = self.candidates(prefix)
        if not matches:
            self.hide()
            return
        self.prefix, self.matches = prefix, matches
        self.show()

    def show(self):
        text = self.tab.text
        bbox = text.bbox("insert")
        if not bbox:
            self.hide()
            return
        if not self.win:
            colours = self.tab.app.theme
            self.win = tk.Toplevel(text)
            self.win.wm_overrideredirect(True)
            self.box = tk.Listbox(self.win, font=self.tab.app.font, bd=1, relief="solid", activestyle="none",
                                  exportselection=False, bg=colours["pop_bg"], fg=colours["fg"],
                                  selectbackground=colours["pop_sel"], selectforeground=colours["fg"])
            self.box.pack()
            self.box.bind("<ButtonRelease-1>", self.on_click)
        self.box.delete(0, "end")
        for word in self.matches:
            self.box.insert("end", word)
        self.box.config(height=len(self.matches), width=max(12, max(len(w) for w in self.matches) + 2))
        self.box.selection_clear(0, "end")
        self.box.selection_set(0)
        x, y, _w, h = bbox
        self.win.wm_geometry(f"+{text.winfo_rootx() + x}+{text.winfo_rooty() + y + h}")

    def hide(self):
        if self.win:
            self.win.destroy()
            self.win = self.box = None

    def move(self, delta):
        current = self.box.curselection()[0] if self.box.curselection() else 0
        new = max(0, min(len(self.matches) - 1, current + delta))
        self.box.selection_clear(0, "end")
        self.box.selection_set(new)
        self.box.see(new)

    def on_click(self, _event):
        self.accept()
        self.tab.text.focus_set()

    def accept(self):
        if not self.visible or not self.box.curselection():
            return False
        word = self.matches[self.box.curselection()[0]]
        self.hide()
        text = self.tab.text
        text.delete(f"insert-{len(self.prefix)}c", "insert")
        line_before = text.get("insert linestart", "insert")
        if word in SNIPPETS and not line_before.strip():
            template = SNIPPETS[word].format(i=line_before)
            cursor = template.index("|")
            start = text.index("insert")
            text.insert("insert", template.replace("|", "", 1))
            text.mark_set("insert", f"{start}+{cursor}c")
            return True
        suffix = "(" if word in HELPER_CALLS else " of " if word in OF_HELPERS else ""
        text.insert("insert", word + suffix)
        return True
