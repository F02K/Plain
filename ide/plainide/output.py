"""The OUTPUT panel under the editor: what the program prints, and a line to type input."""

import tkinter as tk
from tkinter import ttk


class OutputPanel(ttk.Frame):
    def __init__(self, parent, app, on_input):
        super().__init__(parent, style="Panel.TFrame")
        t = app.theme
        self.on_input = on_input
        head = ttk.Frame(self, style="PanelHead.TFrame")
        ttk.Label(head, text="OUTPUT", style="PanelTitle.TLabel", padding=(14, 7, 6, 5)).pack(side="left")
        ttk.Button(head, text="Clear", style="Tool.TButton", command=self.clear).pack(side="right", padx=8, pady=3)
        head.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.text = tk.Text(self, font=app.font, bg=t["panel_bg"], fg=t["fg"], insertbackground=t["fg"],
                            height=9, wrap="word", bd=0, highlightthickness=0, padx=14, pady=6,
                            state="disabled", selectbackground=t["select_bg"],
                            inactiveselectbackground=t["select_bg"])
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.config(yscrollcommand=scroll.set)
        row = ttk.Frame(self, style="Panel.TFrame", padding=(14, 4, 8, 6))
        ttk.Label(row, text="Input", style="Panel.TLabel").pack(side="left")
        self.entry = ttk.Entry(row, state="disabled")
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.entry.bind("<Return>", self._submit)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.text.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        row.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.restyle(t)

    def restyle(self, t):
        self.text.config(bg=t["panel_bg"], fg=t["fg"], insertbackground=t["fg"], selectbackground=t["select_bg"],
                         inactiveselectbackground=t["select_bg"])
        self.text.tag_configure("err", foreground=t["out_err"])
        self.text.tag_configure("in", foreground=t["out_in"])
        self.text.tag_configure("info", foreground=t["out_info"])

    def write(self, text, tag=None):
        self.text.config(state="normal")
        self.text.insert("end", text, tag)
        self.text.config(state="disabled")
        self.text.see("end")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def get(self):
        return self.text.get("1.0", "end").strip()

    def allow_input(self, allowed):
        self.entry.config(state="normal" if allowed else "disabled")
        if allowed:
            self.entry.focus_set()

    def _submit(self, _event):
        line = self.entry.get()
        self.entry.delete(0, "end")
        self.on_input(line)
