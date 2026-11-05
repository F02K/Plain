"""The VALUES view: a list of all variables of the running program, newest changes highlighted."""

import time
import tkinter as tk
from tkinter import ttk

NOTE = ("Run the program to see its values. Values that just changed are highlighted. "
        "Click a row to find it in the code.")


class ValuesPanel(ttk.Frame):
    def __init__(self, parent, app, on_select):
        super().__init__(parent, style="Side.TFrame")
        self.on_select_row = on_select
        self.rows = {}
        self.changed = {}
        ttk.Label(self, text="VALUES", style="SideHead.TLabel", padding=(12, 8, 6, 6)).grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.tree = ttk.Treeview(self, columns=("value", "line"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Name")
        self.tree.heading("value", text="Value")
        self.tree.heading("line", text="Line")
        self.tree.column("#0", width=140, stretch=False)
        self.tree.column("value", width=90, stretch=True)
        self.tree.column("line", width=36, stretch=False, anchor="e")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        self.note = ttk.Label(self, text=NOTE, padding=(12, 6), wraplength=230, style="Side.TLabel")
        self.note.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.restyle(app.theme)

    def restyle(self, t):
        self.tree.tag_configure("changed", background=t["watch_changed"])

    def reset(self):
        self.rows, self.changed = {}, {}
        self.tree.delete(*self.tree.get_children())
        self.note.config(text=NOTE)

    def update_rows(self, rows):
        for name, text, line in rows:
            iid = self.rows.get(name)
            if iid is None:
                self.rows[name] = self.tree.insert("", "end", text=name, values=(text, line))
            elif self.tree.set(iid, "value") != text:
                self.tree.set(iid, "value", text)
                self.tree.set(iid, "line", line)
                self.tree.item(iid, tags=("changed",))
                self.changed[iid] = time.time()

    def fade(self):
        """Take the highlight away from rows that changed a while ago."""
        now = time.time()
        for iid, since in list(self.changed.items()):
            if now - since > 1.2:
                if self.tree.exists(iid):
                    self.tree.item(iid, tags=())
                del self.changed[iid]

    def _selected(self, _event):
        selected = self.tree.selection()
        if not selected:
            return
        name = self.tree.item(selected[0], "text").split(": ")[-1]
        try:
            line = int(self.tree.set(selected[0], "line"))
        except ValueError:
            return
        self.on_select_row(name, line)
