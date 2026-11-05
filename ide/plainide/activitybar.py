"""The narrow bar on the far left with one button per view (Explorer, Values), like Visual Studio Code."""

import tkinter as tk

WIDTH = 48


class ActivityBar(tk.Frame):
    def __init__(self, parent, app, on_pick):
        super().__init__(parent, width=WIDTH, bd=0, highlightthickness=0)
        self.app = app
        self.on_pick = on_pick
        self.pack_propagate(False)
        self.active = None
        self.buttons = {}
        for name in ("explorer", "values"):
            row = tk.Frame(self, height=WIDTH, bd=0, highlightthickness=0, cursor="hand2")
            row.pack(side="top", fill="x")
            row.pack_propagate(False)
            mark = tk.Frame(row, width=2, bd=0, highlightthickness=0)
            mark.pack(side="left", fill="y")
            icon = tk.Label(row, bd=0, cursor="hand2")
            icon.pack(side="left", expand=True)
            for widget in (row, icon):
                widget.bind("<Button-1>", lambda e, n=name: self.on_pick(n))
            self.buttons[name] = (row, mark, icon)
        self.restyle()

    def set_active(self, name):
        self.active = name
        self.restyle()

    def restyle(self):
        t = self.app.theme
        icons = self.app.icons
        self.config(bg=t["activity_bg"])
        for name, (row, mark, icon) in self.buttons.items():
            on = name == self.active
            picture = getattr(icons, name + ("_active" if on else ""))
            row.config(bg=t["activity_bg"])
            mark.config(bg=t["activity_active"] if on else t["activity_bg"])
            icon.config(image=picture, bg=t["activity_bg"])
