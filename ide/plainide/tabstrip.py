"""The row of tabs above the editor, like Visual Studio Code: a close button on every tab,
a dot on tabs with unsaved changes, a colored line on the tab you are in."""

import tkinter as tk

HEIGHT = 36


class TabStrip(tk.Frame):
    def __init__(self, parent, app, on_select, on_close, on_menu):
        super().__init__(parent, height=HEIGHT, bd=0, highlightthickness=0)
        self.app = app
        self.on_select, self.on_close, self.on_menu = on_select, on_close, on_menu
        self.pack_propagate(False)
        self.canvas = tk.Canvas(self, height=HEIGHT, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bd=0, highlightthickness=0)
        self.canvas.create_window(0, 0, window=self.inner, anchor="nw", height=HEIGHT)
        self.inner.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Configure>", self._on_resize)
        for widget in (self.canvas, self.inner):
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Button-4>", self._on_wheel)
            widget.bind("<Button-5>", self._on_wheel)
        self.items = {}         # document -> widgets of its tab
        self.selected = None
        self.hover = None
        self.restyle()

    # ---- the tabs --------------------------------------------------------------

    def add(self, doc):
        t = self.app.theme
        tab = tk.Frame(self.inner, bd=0, highlightthickness=0, cursor="hand2")
        line = tk.Frame(tab, height=2, bd=0, highlightthickness=0)
        line.pack(side="top", fill="x")
        label = tk.Label(tab, text=doc.name, font=self.app.ui_font, padx=12, pady=0, bd=0, anchor="w")
        label.pack(side="left", fill="y")
        close = tk.Label(tab, text="×", font=(self.app.ui_font[0], 13), width=2, bd=0, cursor="arrow")
        close.pack(side="right", fill="y", padx=(0, 6))
        for widget in (tab, label, line):
            widget.bind("<Button-1>", lambda e, d=doc: self.on_select(d))
            widget.bind("<ButtonRelease-2>", lambda e, d=doc: self.on_close(d))
            widget.bind("<Button-3>", lambda e, d=doc: self.on_menu(d, e))
        close.bind("<Button-1>", lambda e, d=doc: self.on_close(d))
        for widget in (tab, label, close, line):
            widget.bind("<Enter>", lambda e, d=doc: self._hover(d))
            widget.bind("<Leave>", lambda e, d=doc: self._hover(None))
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Button-4>", self._on_wheel)
            widget.bind("<Button-5>", self._on_wheel)
        tab.pack(side="left", fill="y", padx=(0, 1))
        self.items[doc] = {"tab": tab, "line": line, "label": label, "close": close}
        self.update(doc)

    def remove(self, doc):
        parts = self.items.pop(doc, None)
        if parts:
            parts["tab"].destroy()
        if self.selected is doc:
            self.selected = None

    def select(self, doc):
        self.selected = doc
        for d in self.items:
            self._paint(d)
        self.see(doc)

    def update(self, doc):
        """Title and the dot for unsaved changes."""
        if doc in self.items:
            self.items[doc]["label"].config(text=doc.name)
            self._paint(doc)

    def restyle(self):
        t = self.app.theme
        self.config(bg=t["tabstrip_bg"])
        self.canvas.config(bg=t["tabstrip_bg"])
        self.inner.config(bg=t["tabstrip_bg"])
        for doc in self.items:
            self._paint(doc)

    # ---- drawing ---------------------------------------------------------------

    def _hover(self, doc):
        old, self.hover = self.hover, doc
        for d in (old, doc):
            if d in self.items:
                self._paint(d)

    def _paint(self, doc):
        t = self.app.theme
        parts = self.items[doc]
        active = doc is self.selected
        bg = t["bg"] if active else t["tab_hover_bg"] if doc is self.hover else t["tab_bg"]
        fg = t["fg"] if active else t["out_info"]
        parts["tab"].config(bg=bg)
        parts["line"].config(bg=t["accent"] if active else bg)
        parts["label"].config(bg=bg, fg=fg)
        hovered = doc is self.hover
        if doc.dirty and not hovered:
            parts["close"].config(text="●", font=(self.app.ui_font[0], 9), bg=bg, fg=fg)
        else:
            show = active or hovered
            parts["close"].config(text="×", font=(self.app.ui_font[0], 13), bg=bg, fg=fg if show else bg)

    # ---- scrolling when there are many tabs ------------------------------------------

    def _on_resize(self, _event=None):
        width = max(self.inner.winfo_reqwidth(), self.canvas.winfo_width())
        self.canvas.config(scrollregion=(0, 0, width, HEIGHT))

    def _on_wheel(self, event):
        step = -1 if (event.num == 4 or getattr(event, "delta", 0) > 0) else 1
        self.canvas.xview_scroll(step * 3, "units")
        return "break"

    def see(self, doc):
        """Scroll so that the tab of the document is fully visible."""
        parts = self.items.get(doc)
        if not parts:
            return
        self.update_idletasks()
        total = max(self.inner.winfo_reqwidth(), 1)
        left, right = parts["tab"].winfo_x(), parts["tab"].winfo_x() + parts["tab"].winfo_width()
        view_left, view_right = (f * total for f in self.canvas.xview())
        if left < view_left:
            self.canvas.xview_moveto(left / total)
        elif right > view_right:
            self.canvas.xview_moveto(max(0, (right - self.canvas.winfo_width()) / total))
