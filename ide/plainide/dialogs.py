"""Small windows: project settings and the quick reference."""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import TITLE
from . import projects as PROJECTS
from .helptext import CHEAT_SHEET


def project_settings_dialog(app, info, done):
    """Name, main program and program file name of a project. done(old project file path) runs after Save."""
    win = tk.Toplevel(app.root)
    win.title(f"Project settings - {info.name}")
    win.transient(app.root)
    win.resizable(False, False)
    win.configure(bg=app.theme["ui_bg"])
    frame = ttk.Frame(win, padding=14)
    frame.pack()
    name = tk.StringVar(value=info.name)
    main = tk.StringVar(value=info.main)
    output = tk.StringVar(value=info.output)
    ttk.Label(frame, text="Name").grid(row=0, column=0, sticky="w", pady=4)
    ttk.Entry(frame, textvariable=name, width=34).grid(row=0, column=1, pady=4, padx=(10, 0))
    ttk.Label(frame, text="Main program").grid(row=1, column=0, sticky="w", pady=4)
    ttk.Combobox(frame, textvariable=main, values=info.plain_files() or [info.main], width=32,
                 state="readonly").grid(row=1, column=1, pady=4, padx=(10, 0))
    ttk.Label(frame, text="Program file name").grid(row=2, column=0, sticky="w", pady=4)
    ttk.Entry(frame, textvariable=output, width=34).grid(row=2, column=1, pady=4, padx=(10, 0))
    ttk.Label(frame, text="The main program is what Build and Release turn into a Python file and a program.\n"
                          "You can also edit the .plainproject file as text.",
              wraplength=380).grid(row=3, column=0, columnspan=2, pady=(8, 0))

    def apply():
        old = info.path
        info.name = name.get().strip() or info.name
        info.main = main.get() or info.main
        info.output = PROJECTS.slug(output.get() or info.name)
        info.file = None                    # the file is named after the project again
        try:
            info.save()
            if info.path != old and os.path.exists(old):
                os.remove(old)
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot save the project: {exc.strerror}", parent=win)
            return
        win.destroy()
        done(old)

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, pady=(12, 0), sticky="e")
    ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side="right")
    ttk.Button(buttons, text="Save", command=apply).pack(side="right", padx=(0, 8))


def help_window(app):
    win = tk.Toplevel(app.root)
    win.title("Plain quick reference")
    win.configure(bg=app.theme["bg"])
    box = tk.Text(win, font=app.font, width=88, height=34, padx=14, pady=10, wrap="none", bd=0,
                  bg=app.theme["bg"], fg=app.theme["fg"], insertbackground=app.theme["fg"])
    box.insert("1.0", CHEAT_SHEET)
    box.config(state="disabled")
    box.pack(fill="both", expand=True)
