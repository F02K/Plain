# The Python code of the window module (see window.plain). It is copied into every program that says
# "import window", so the program is one file that runs with plain Python. It uses tkinter.
#
# How Plain and this file fit together:
#   * `export Window as window to python "window_impl"` means: the class Window below IS the Plain type Window.
#     Its constructor gets the fields that are not readonly, in the order of `define Window` (title, width, ...).
#     Reading `open of win` reads the attribute `open`; `set color of win to red` sets the attribute `color`.
#   * Every line of the `from python` block is a function below. It gets the thing it works on first, then its
#     values in order, and the line number of the Plain line last (to report mistakes at the right line).
#   * A Plain thing that arrives here (a Color) has its fields named f_red, f_green, f_blue.
#   * raise _PlainError("message", line) to report a problem the Plain way (it can be caught with try).
import os as _os
import time as _time

_KEYS = {
    "left": ("left",), "right": ("right",), "up": ("up",), "down": ("down",), "space": ("space",),
    "enter": ("return",), "escape": ("escape",), "tab": ("tab",), "backspace": ("backspace",),
    "shift": ("shift_l", "shift_r"), "ctrl": ("control_l", "control_r"),
}


def _hex(color):
    def part(v):
        return max(0, min(255, int(v)))
    return "#%02x%02x%02x" % (part(color.f_red), part(color.f_green), part(color.f_blue))


class Window:
    current = None          # the window that is open (only one at a time)

    def __init__(self, title, width, height, background, color):
        w, h = int(width), int(height)
        if not (1 <= w <= 4000 and 1 <= h <= 4000):
            raise _PlainError("The window size must be between 1 and 4000.")
        if Window.current is not None and Window.current.open:
            raise _PlainError("A window is already open.")
        self.title = title
        self._size = (w, h)
        self.background = background
        self.color = color
        self.open = True
        self.keys = set()
        self.mouse = [0, 0]
        self.down = False
        self.tk = None
        self.root = None
        self.canvas = None
        # PLAIN_HEADLESS is for tests: the program runs the same, but nothing is drawn on the screen.
        self.headless = bool(_os.environ.get("PLAIN_HEADLESS"))
        if not self.headless:
            import tkinter
            try:
                self.root = tkinter.Tk()
            except tkinter.TclError:
                raise _PlainError("I could not open the window.")
            self.tk = tkinter
            self.root.title(title)
            self.root.resizable(False, False)
            self.canvas = tkinter.Canvas(self.root, width=w, height=h, bg="#ffffff", highlightthickness=0, bd=0)
            self.canvas.pack()
            self.root.protocol("WM_DELETE_WINDOW", self._closed)
            self.root.bind("<KeyPress>", lambda e: self.keys.add(e.keysym.lower()))
            self.root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym.lower()))
            self.canvas.bind("<Motion>", self._moved)
            self.canvas.bind("<ButtonPress-1>", self._pressed(True))
            self.canvas.bind("<ButtonRelease-1>", self._pressed(False))
            self.root.focus_force()
        Window.current = self

    # ---- what Plain reads: open of win, mouse_x of win, width of win ...
    @property
    def mouse_x(self):
        return float(self.mouse[0])

    @property
    def mouse_y(self):
        return float(self.mouse[1])

    @property
    def mouse_down(self):
        return self.down and self.open

    @property
    def width(self):
        return float(self._size[0])

    @width.setter
    def width(self, value):
        raise _PlainError("The size of a window cannot be changed after it is opened.")

    @property
    def height(self):
        return float(self._size[1])

    @height.setter
    def height(self, value):
        raise _PlainError("The size of a window cannot be changed after it is opened.")

    # ---- events from tkinter
    def _closed(self):
        self.open = False
        self.root.destroy()

    def _moved(self, event):
        self.mouse[:] = [event.x, event.y]

    def _pressed(self, state):
        def handler(event):
            self.down = state
            self.mouse[:] = [event.x, event.y]
        return handler

    def draw(self, action):
        if self.open and self.canvas is not None:
            try:
                action(self.canvas)
            except self.tk.TclError:
                self.open = False


# ---- the actions and questions of the `from python` block --------------------------------------------

def clear(window, line):
    def action(canvas):
        canvas.delete("all")
        canvas.configure(bg=_hex(window.background))
    window.draw(action)


def show(window, line):
    if window.open and window.root is not None:
        try:
            window.root.update()
        except window.tk.TclError:
            window.open = False
        _time.sleep(0.015)


def close(window, line):
    if window.open:
        window.open = False
        if window.root is not None:
            try:
                window.root.destroy()
            except window.tk.TclError:
                pass


def draw_rectangle(window, x, y, width, height, color, line):
    window.draw(lambda c: c.create_rectangle(int(x), int(y), int(x) + int(width) - 1, int(y) + int(height) - 1,
                                             fill=_hex(color), width=0))


def draw_circle(window, x, y, radius, color, line):
    window.draw(lambda c: c.create_oval(int(x) - int(radius), int(y) - int(radius), int(x) + int(radius),
                                        int(y) + int(radius), fill=_hex(color), width=0))


def draw_line(window, x1, y1, x2, y2, color, line):
    window.draw(lambda c: c.create_line(int(x1), int(y1), int(x2), int(y2), fill=_hex(color), width=2))


def draw_text(window, text, x, y, color, line):
    window.draw(lambda c: c.create_text(int(x), int(y), anchor="nw", text=text, fill=_hex(color),
                                        font=("Segoe UI", -20)))


def is_down(window, key, line):
    if key in _KEYS:
        wanted = _KEYS[key]
    elif len(key) == 1 and key.isalnum() and key.isascii():
        wanted = (key.lower(),)
    else:
        raise _PlainError("I do not know that key. Use left, right, up, down, space, enter, escape, shift, "
                          "ctrl, tab, backspace, a-z or 0-9.", line)
    return window.open and any(k in window.keys for k in wanted)


def _finish():
    """When the program ends while the window is still open, keep it on screen until it is closed."""
    window = Window.current
    if window is not None and window.open and window.root is not None:
        try:
            window.root.mainloop()
        except window.tk.TclError:
            pass


_FINISHERS.append(_finish)
