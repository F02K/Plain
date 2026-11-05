"""The bar under the menu: Run, Stop, Build, Release, the live-value switches."""

from tkinter import ttk


class Toolbar(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Toolbar.TFrame", padding=(8, 5))
        self.run_button = ttk.Button(self, text="▶  Run  F5", style="Run.TButton", command=app.running.run)
        self.run_button.pack(side="left")
        self.stop_button = ttk.Button(self, text="■  Stop", style="Tool.TButton", command=app.running.stop,
                                      state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=14, pady=3)
        self.build_button = ttk.Button(self, text="Build  F6", style="Tool.TButton", command=app.building.build)
        self.build_button.pack(side="left")
        self.release_button = ttk.Button(self, text="Release  F7", style="Tool.TButton",
                                         command=app.building.release)
        self.release_button.pack(side="left", padx=(6, 0))
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=14, pady=3)
        ttk.Checkbutton(self, text="Live values", style="Toolbar.TCheckbutton",
                        variable=app.live_var).pack(side="left")
        ttk.Checkbutton(self, text="Value list", style="Toolbar.TCheckbutton", variable=app.watch_var,
                        command=app.toggle_values).pack(side="left", padx=(10, 0))
        ttk.Button(self, text="Dark / Light", style="Tool.TButton", command=app.toggle_theme).pack(side="right")
