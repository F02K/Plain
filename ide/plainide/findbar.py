"""Find and replace inside one editor tab (Ctrl+F, Ctrl+H), like in Visual Studio Code.

All matches are marked, the current one stands out. Enter goes to the next match, Shift+Enter to the
one before, Esc closes the bar."""

import tkinter as tk
from tkinter import ttk


class FindBar(tk.Frame):
    def __init__(self, tab):
        super().__init__(tab, bd=0, highlightthickness=0)
        self.tab = tab
        self.text = tab.text
        self.find_var = tk.StringVar(master=tab)
        self.replace_var = tk.StringVar(master=tab)
        self.case_var = tk.BooleanVar(master=tab, value=False)
        self.matches = []               # [(start index, end index)]
        self.current = -1
        t = tab.app.theme
        ui = tab.app.ui_font

        top = tk.Frame(self, bd=0, highlightthickness=0)
        top.pack(fill="x", padx=8, pady=(6, 2))
        self.find_label = tk.Label(top, text="Find", font=ui, width=8, anchor="w", bd=0)
        self.find_label.pack(side="left")
        self.find_entry = tk.Entry(top, textvariable=self.find_var, font=ui, bd=0, relief="flat", width=30,
                                   highlightthickness=1)
        self.find_entry.pack(side="left", ipady=3)
        self.case = tk.Checkbutton(top, text="Aa", variable=self.case_var, font=ui, bd=0, indicatoron=False,
                                   padx=6, pady=1, command=self.update, cursor="hand2")
        self.case.pack(side="left", padx=(6, 0))
        self.count = tk.Label(top, text="", font=ui, width=12, anchor="w", bd=0)
        self.count.pack(side="left", padx=(8, 0))
        self.buttons = []
        for text, command in (("Previous", self.previous), ("Next", self.next), ("Close", self.hide)):
            button = tk.Button(top, text=text, font=ui, command=command, bd=0, padx=8, pady=1, cursor="hand2")
            button.pack(side="left", padx=(4, 0))
            self.buttons.append(button)

        self.replace_row = tk.Frame(self, bd=0, highlightthickness=0)
        self.replace_label = tk.Label(self.replace_row, text="Replace", font=ui, width=8, anchor="w", bd=0)
        self.replace_label.pack(side="left")
        self.replace_entry = tk.Entry(self.replace_row, textvariable=self.replace_var, font=ui, bd=0,
                                      relief="flat", width=30, highlightthickness=1)
        self.replace_entry.pack(side="left", ipady=3)
        for text, command in (("Replace", self.replace_one), ("Replace all", self.replace_all)):
            button = tk.Button(self.replace_row, text=text, font=ui, command=command, bd=0, padx=8, pady=1,
                               cursor="hand2")
            button.pack(side="left", padx=(4, 0))
            self.buttons.append(button)

        self.find_entry.bind("<Return>", lambda e: self.next() or "break")
        self.find_entry.bind("<Shift-Return>", lambda e: self.previous() or "break")
        self.replace_entry.bind("<Return>", lambda e: self.replace_one() or "break")
        for entry in (self.find_entry, self.replace_entry):
            entry.bind("<Escape>", lambda e: self.hide() or "break")
            entry.bind("<F3>", lambda e: self.next() or "break")
            entry.bind("<Shift-F3>", lambda e: self.previous() or "break")
        self.find_entry.bind("<KeyRelease>", lambda e: self.update(jump=e.keysym not in ("Return", "Escape")))
        self.restyle()

    # ---- look ----------------------------------------------------------------

    def restyle(self):
        t = self.tab.app.theme
        self.config(bg=t["ui_bg"])
        for frame in (self.find_label.master, self.replace_row):
            frame.config(bg=t["ui_bg"])
        for label in (self.find_label, self.replace_label, self.count):
            label.config(bg=t["ui_bg"], fg=t["fg"])
        for entry in (self.find_entry, self.replace_entry):
            entry.config(bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"], highlightbackground=t["border"],
                         highlightcolor=t["accent"])
        for button in self.buttons:
            button.config(bg=t["button_bg"], fg=t["fg"], activebackground=t["button_hover"],
                          activeforeground=t["fg"])
        self.case.config(bg=t["button_bg"], fg=t["fg"], selectcolor=t["accent"], activebackground=t["button_hover"],
                         activeforeground=t["fg"])
        self.text.tag_configure("find_match", background=t["find_match"])
        self.text.tag_configure("find_current", background=t["find_current"])
        self.text.tag_lower("find_match")
        self.text.tag_lower("find_current")
        self.text.tag_raise("sel")

    # ---- showing and hiding ----------------------------------------------------

    @property
    def visible(self):
        return bool(self.winfo_manager())

    def show(self, replace=False):
        self.grid(row=3, column=0, columnspan=3, sticky="ew")
        if replace:
            self.replace_row.pack(fill="x", padx=8, pady=(0, 6))
        else:
            self.replace_row.pack_forget()
        try:                                    # start with the selected word
            chosen = self.text.get("sel.first", "sel.last")
            if chosen and "\n" not in chosen:
                self.find_var.set(chosen)
        except tk.TclError:
            pass
        self.find_entry.focus_set()
        self.find_entry.selection_range(0, "end")
        self.update()

    def hide(self):
        self.grid_remove()
        self.clear()
        self.text.focus_set()

    def clear(self):
        for tag in ("find_match", "find_current"):
            self.text.tag_remove(tag, "1.0", "end")
        self.matches, self.current = [], -1

    # ---- searching -------------------------------------------------------------

    def find_all(self):
        pattern = self.find_var.get()
        found = []
        if not pattern:
            return found
        index = "1.0"
        length = tk.IntVar(master=self.text)
        while True:
            start = self.text.search(pattern, index, stopindex="end", nocase=not self.case_var.get(), count=length)
            if not start or length.get() == 0:
                break
            end = f"{start}+{length.get()}c"
            found.append((start, end))
            index = end
        return found

    def update(self, jump=True):
        """Mark all matches (again), and go to the first one at or after the cursor."""
        self.clear()
        self.matches = self.find_all()
        for start, end in self.matches:
            self.text.tag_add("find_match", start, end)
        if not self.find_var.get():
            self.count.config(text="")
            return
        if not self.matches:
            self.count.config(text="No results")
            return
        if jump:
            cursor = self.text.index("insert")
            self.current = next((i for i, (s, _e) in enumerate(self.matches) if self.text.compare(s, ">=", cursor)), 0)
            self.show_current()
        else:
            self.count.config(text=f"{len(self.matches)} found")

    def show_current(self):
        for tag in ("find_current",):
            self.text.tag_remove(tag, "1.0", "end")
        start, end = self.matches[self.current]
        self.text.tag_add("find_current", start, end)
        self.text.mark_set("insert", end)
        self.text.see(start)
        self.count.config(text=f"{self.current + 1} of {len(self.matches)}")

    def step(self, delta):
        if not self.visible and self.find_var.get():
            self.show()
        if not self.matches:
            self.matches = self.find_all()
        if not self.matches:
            return
        self.current = (self.current + delta) % len(self.matches)
        self.show_current()

    def next(self):
        self.step(1)

    def previous(self):
        self.step(-1)

    # ---- replacing -------------------------------------------------------------

    def replace_one(self):
        if not self.matches:
            self.update()
        if not self.matches or self.current < 0:
            return
        start, end = self.matches[self.current]
        self.replace_range([(start, end)])
        self.update()

    def replace_range(self, matches):
        """Replace the matches (from the end, so the positions stay right) as ONE step for Undo."""
        self.text.config(autoseparators=False)
        try:
            self.text.edit_separator()
            for start, end in reversed(matches):
                self.text.delete(start, end)
                self.text.insert(start, self.replace_var.get())
            self.text.edit_separator()
        finally:
            self.text.config(autoseparators=True)

    def replace_all(self):
        matches = self.find_all()
        if not matches:
            return
        self.replace_range(matches)
        self.update(jump=False)
        self.count.config(text=f"{len(matches)} replaced")
