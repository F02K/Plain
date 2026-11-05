"""The colored bar at the bottom: blue when idle, orange while a program runs or is built."""

from tkinter import ttk


class StatusBar(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Status.TFrame")
        self.text, self.busy = "Ready", False
        self.labels = []
        for text, side in (("Ready", "left"), ("", "left"), ("", "left"), ("Plain", "right"), ("Spaces: 4", "right"),
                           ("Ln 1, Col 1", "right")):
            label = ttk.Label(self, text=text, style="Status.TLabel")
            label.pack(side=side)
            self.labels.append(label)
        self.left, self.project, self.problem, self.language, self.indent, self.position = self.labels
        self.problem.config(cursor="hand2")
        self.problem_line = None
        self.on_problem_click = None
        self.problem.bind("<Button-1>", lambda e: self.on_problem_click and self.problem_line
                          and self.on_problem_click(self.problem_line))

    def set(self, text, busy=False):
        self.text, self.busy = text, busy
        self.refresh_style()
        self.left.config(text=text)

    def refresh_style(self):
        suffix = "Busy" if self.busy else ""
        self.config(style=f"Status{suffix}.TFrame")
        for label in self.labels:
            label.config(style=f"Status{suffix}.TLabel")

    def set_problem(self, line, message):
        """The first mistake the IDE found while you type (click it to go there). Empty: no mistake."""
        self.problem_line = line
        if line is None:
            self.problem.config(text="")
            return
        message = message if len(message) <= 70 else message[:67] + "..."
        self.problem.config(text=f"Problem, line {line}: {message}")

    def set_position(self, line, col):
        self.position.config(text=f"Ln {line}, Col {col}")

    def set_project(self, text):
        self.project.config(text=text)

    def set_language(self, text):
        self.language.config(text=text)
