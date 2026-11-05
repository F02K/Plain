"""One editor tab: the text, line numbers, colors, live values and the typing help."""

import os
import re
import tkinter as tk
from tkinter import ttk

from plain.lexer import KEYWORDS

from .completer import Completer
from .language import (COLOR_WORD, HELPERS, INDENT, NEW_PROGRAM, OPENERS, PHRASES, PROJECT_KEYS, kind_of)
from .symbols import TOKEN, analyze


class EditorTab(ttk.Frame):
    """One open file: the text, the line numbers, the highlighting and the typing help."""

    def __init__(self, app, parent, path=None, content=NEW_PROGRAM, untitled=None):
        super().__init__(parent)
        self.app = app
        self.path = path
        self.dirty = False
        self.highlight_job = None
        self.symbol_job = None
        self.inline = {}          # line number -> text shown behind the code while the program runs
        self.inline_labels = {}
        self.line_count = 0
        self.untitled = untitled          # "Untitled 1" while the file has no path
        font = app.font

        self.gutter = tk.Text(self, width=4, padx=10, pady=6, font=font, bd=0, highlightthickness=0,
                              state="disabled", cursor="arrow", takefocus=0, wrap="none", spacing1=1, spacing3=1)
        self.gutter.tag_configure("right", justify="right")
        self.text = tk.Text(self, font=font, undo=True, wrap="none", bd=0, highlightthickness=0, padx=8, pady=6,
                            tabs=(font.measure(INDENT),), spacing1=1, spacing3=1)
        self.yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.config(yscrollcommand=self.on_yscroll,
                         xscrollcommand=lambda a, b: (xscroll.set(a, b), self.refresh_inline()))
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.yscroll.grid(row=0, column=2, sticky="ns")
        xscroll.grid(row=1, column=1, sticky="ew")
        self.info = ttk.Label(self, text="", anchor="w", padding=(12, 3), style="Info.TLabel")
        self.info.grid(row=2, column=0, columnspan=3, sticky="ew")

        self.restyle()
        self.text.tag_lower("current_line")
        self.text.tag_lower("symbol")
        self.text.tag_lower("symbol_def")
        self.text.tag_raise("sel")

        self.completer = Completer(self)
        self.text.bind("<<Modified>>", self.on_modified)
        self.text.bind("<Return>", self.on_return)
        self.text.bind("<Tab>", self.on_tab)
        self.text.bind("<Up>", lambda e: self.on_arrow(-1))
        self.text.bind("<Down>", lambda e: self.on_arrow(1))
        self.text.bind("<Escape>", lambda e: self.completer.hide())
        for key in ("<Left>", "<Right>", "<Home>", "<End>", "<Prior>", "<Next>"):
            self.text.bind(key, lambda e: self.completer.hide(), add="+")
        self.text.bind("<Control-space>", lambda e: (self.completer.update(force=True), "break")[1])
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<ButtonRelease-1>", lambda e: (self.completer.hide(), self.clear_marks(), self.schedule_symbol(),
                                                       self.update_cursor()))
        self.text.bind("<Control-Button-1>", self.goto_definition)
        # The text widget has its own Ctrl keys (Ctrl+O opens a new line...), so route ours through it.
        app.bind_shortcuts(self.text)
        self.gutter.bind("<MouseWheel>", self.on_wheel)
        self.gutter.bind("<Button-4>", self.on_wheel)
        self.gutter.bind("<Button-5>", self.on_wheel)

        self.set_text(content)

    def restyle(self):
        """Colors from the current theme (called when the tab is made and when the theme changes)."""
        t = self.app.theme
        self.gutter.config(bg=t["gutter_bg"], fg=t["gutter_fg"])
        self.text.config(bg=t["bg"], fg=t["fg"], insertbackground=t["fg"], selectbackground=t["select_bg"],
                         selectforeground=t["fg"], inactiveselectbackground=t["select_bg"])
        for tag in ("keyword", "helper", "string", "number", "comment"):
            self.text.tag_configure(tag, foreground=t[tag])
        self.text.tag_configure("error_line", background=t["error_line"])
        self.text.tag_configure("current_line", background=t["current_line"])
        self.text.tag_configure("symbol", background=t["symbol"])
        self.text.tag_configure("symbol_def", background=t["symbol_def"], underline=True)
        for label in self.inline_labels.values():
            label.config(fg=t["inline_fg"], bg=t["inline_bg"])

    def update_cursor(self):
        """Mark the line of the cursor and tell the status bar where it is."""
        self.text.tag_remove("current_line", "1.0", "end")
        if self.text.tag_ranges("sel"):
            return
        line, col = (int(n) for n in self.text.index("insert").split("."))
        self.text.tag_add("current_line", f"{line}.0", f"{line}.end+1c")
        if self.app.documents.current() is self:
            self.app.update_position(line, col + 1)

    # ---- file state ----------------------------------------------------------

    @property
    def kind(self):
        """'plain' (a program), 'project' (a .plainproject file) or 'text' (any other file)."""
        return kind_of(self.path)

    @property
    def name(self):
        return os.path.basename(self.path) if self.path else self.untitled

    def source(self):
        return self.text.get("1.0", "end-1c")

    def set_text(self, content):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.dirty = False
        self.rehighlight()
        self.update_gutter()
        self.clear_marks()

    def on_modified(self, _event):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        if not self.dirty:
            self.dirty = True
            self.app.documents.refresh()
        self.update_gutter()
        if self.inline and not self.app.runner.running:
            self.clear_inline()     # the lines may have moved, so the old values no longer fit
        if self.highlight_job:
            self.after_cancel(self.highlight_job)
        self.highlight_job = self.after(120, self.rehighlight)

    # ---- look ----------------------------------------------------------------

    def on_yscroll(self, first, last):
        self.yscroll.set(first, last)
        self.gutter.yview_moveto(first)
        self.refresh_inline()

    # ---- live values behind the code -----------------------------------------

    def set_inline(self, lines):
        changed = {n for n, text in lines.items() if self.inline.get(n) != text}
        self.inline = lines
        self.refresh_inline(changed)

    def clear_inline(self):
        self.inline = {}
        for label in self.inline_labels.values():
            label.destroy()
        self.inline_labels = {}

    def refresh_inline(self, changed=()):
        if not self.inline and not self.inline_labels:
            return
        t = self.app.theme
        try:
            first = int(self.text.index("@0,0").split(".")[0])
            last = int(self.text.index(f"@0,{self.text.winfo_height()}").split(".")[0])
        except (tk.TclError, ValueError):
            return
        small = self.app.small_font
        for n, label in list(self.inline_labels.items()):
            if n not in self.inline or not first <= n <= last:
                label.place_forget()
        for n in range(first, last + 1):
            text = self.inline.get(n)
            box = self.text.bbox(f"{n}.end") if text else None
            if not box:
                continue
            x, y, w, h = box
            label = self.inline_labels.get(n)
            if label is None:
                label = tk.Label(self.text, font=small, fg=t["inline_fg"], bg=t["inline_bg"], padx=6, pady=0,
                                 anchor="w", bd=0)
                self.inline_labels[n] = label
            shown = text.replace("->", "→")
            if label.cget("text") != shown:
                label.config(text=shown)
            label.place(x=x + 18, y=y, height=h)
            if n in changed:
                label.config(bg=t["watch_changed"])
                self.after(700, lambda lb=label: lb.winfo_exists() and lb.config(bg=t["inline_bg"]))

    def on_wheel(self, event):
        step = -1 if (event.num == 4 or getattr(event, "delta", 0) > 0) else 1
        self.text.yview_scroll(step * 3, "units")
        return "break"

    def update_gutter(self):
        count = int(self.text.index("end-1c").split(".")[0])
        if count == self.line_count:
            return
        self.line_count = count
        self.gutter.config(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)), "right")
        self.gutter.config(state="disabled")
        self.gutter.yview_moveto(self.text.yview()[0])

    def rehighlight(self):
        self.highlight_job = None
        for tag in ("keyword", "helper", "string", "number", "comment"):
            self.text.tag_remove(tag, "1.0", "end")
        source = self.source()
        kind = self.kind
        if kind == "text":
            return
        if kind == "project":
            self.highlight_project(source)
            return
        quiet = []  # comments and texts: sentence words inside them stay plain
        for m in TOKEN.finditer(source):
            kind = m.lastgroup
            if kind in ("comment", "string"):
                quiet.append((m.start(), m.end()))
            if kind == "word":
                word = m.group()
                kind = "keyword" if word in KEYWORDS else "helper" if word in HELPERS else None
                if kind is None:
                    continue
            self.text.tag_add(kind, f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for pattern in (PHRASES, COLOR_WORD):
            for m in pattern.finditer(source):
                if not any(a <= m.start() < b for a, b in quiet):
                    self.text.tag_add("helper", f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    def highlight_project(self, source):
        """A .plainproject file: the words 'name', 'main' and 'output', and notes."""
        for m in PROJECT_KEYS.finditer(source):
            self.text.tag_add("keyword", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in re.finditer(r"^note:.*$", source, re.M):
            self.text.tag_add("comment", f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    def clear_marks(self):
        self.text.tag_remove("error_line", "1.0", "end")

    # ---- understanding a name ------------------------------------------------

    def schedule_symbol(self):
        if self.symbol_job:
            self.after_cancel(self.symbol_job)
        self.symbol_job = self.after(150, self.update_symbol)

    def update_symbol(self):
        """Mark where the name under the cursor is created (strong) and used (light) and explain it."""
        self.symbol_job = None
        for tag in ("symbol", "symbol_def"):
            self.text.tag_remove(tag, "1.0", "end")
        if self.kind != "plain":
            self.info.config(text="")
            return
        line, col = (int(n) for n in self.text.index("insert").split("."))
        try:
            found = analyze(self.source(), line, col)
        except Exception:  # an explanation must never get in the way of typing
            found = None
        if not found:
            self.info.config(text="")
            return
        self.info.config(text=f"{found['word']}   -   {found['text']}" if found["text"] else "")
        for tag, spans in (("symbol", found["uses"]), ("symbol_def", found["defs"])):
            for a, b in spans:
                self.text.tag_add(tag, f"1.0+{a}c", f"1.0+{b}c")

    def goto_definition(self, event):
        if self.kind != "plain":
            return None
        line, col = (int(n) for n in self.text.index(f"@{event.x},{event.y}").split("."))
        found = analyze(self.source(), line, col)
        if found and found["defs"]:
            self.text.mark_set("insert", f"1.0+{found['defs'][0][0]}c")
            self.text.see("insert")
            self.update_symbol()
        return "break"

    def show_name(self, name, line):
        """Used by the value watcher: jump to the line where a value changed and explain the name."""
        text = self.text.get(f"{line}.0", f"{line}.end")
        m = re.search(r"\b" + re.escape(name) + r"\b", text)
        self.text.mark_set("insert", f"{line}.{m.start() if m else 0}")
        self.text.see("insert")
        self.update_symbol()

    def mark_line(self, line):
        if line and line >= 1:
            self.text.tag_add("error_line", f"{line}.0", f"{line}.end+1c")
            self.text.see(f"{line}.0")

    # ---- typing help ---------------------------------------------------------

    def on_return(self, _event):
        if self.completer.visible:
            self.completer.accept()
            return "break"
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r" *", line).group()
        code = re.sub(r"\bnote:.*$", "", line).strip()
        if self.kind == "plain" and (OPENERS.search(code) or code in ("try", "else")):
            indent += INDENT
        self.text.insert("insert", "\n" + indent)
        self.text.see("insert")
        return "break"

    def on_tab(self, _event):
        if self.completer.visible:
            self.completer.accept()
        else:
            self.text.insert("insert", INDENT)
        return "break"

    def on_arrow(self, delta):
        if self.completer.visible:
            self.completer.move(delta)
            return "break"
        return None

    def on_key_release(self, event):
        key = event.keysym
        self.schedule_symbol()
        self.update_cursor()
        if self.kind != "plain":
            return
        if not (len(key) == 1 and (key.isalnum() or key == "_")) and key not in ("BackSpace", "Delete"):
            return
        # Pull 'end', 'else' and 'catch' back to the level of the block they close.
        line = self.text.get("insert linestart", "insert lineend")
        word = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if word in ("end", "else", "catch") and indent >= len(INDENT) and line.endswith(word) \
                and self.text.index("insert") == self.text.index("insert lineend"):
            self.text.delete("insert linestart", f"insert linestart+{len(INDENT)}c")
        self.completer.update()

