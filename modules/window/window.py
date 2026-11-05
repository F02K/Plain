# The Python code of the window module (see window.plain). It is copied into every program that says
# "import window", so the program is one file that runs with plain Python. It uses tkinter.
import os as _os
import time as _time

_window = None
_window_color_hex = "#000000"

_KEYS = {
    "left": ("left",), "right": ("right",), "up": ("up",), "down": ("down",), "space": ("space",),
    "enter": ("return",), "escape": ("escape",), "tab": ("tab",), "backspace": ("backspace",),
    "shift": ("shift_l", "shift_r"), "ctrl": ("control_l", "control_r"),
}


class _WindowState:
    pass


def _need_window(line):
    if _window is None:
        raise _PlainError('Open a window first, for example: open window "My game" with width 640 and height 480.',
                          line)
    return _window


def window_open(title, width, height, line):
    global _window
    if _window is not None and _window.open:
        raise _PlainError("A window is already open.", line)
    w, h = int(width), int(height)
    if not (1 <= w <= 4000 and 1 <= h <= 4000):
        raise _PlainError("The window size must be between 1 and 4000.", line)
    g = _WindowState()
    g.open = True
    g.color = _window_color_hex
    g.keys = set()
    g.mouse = [0, 0]
    g.down = False
    g.tk = None
    g.root = None
    g.canvas = None
    # PLAIN_HEADLESS is for tests: the program runs the same, but nothing is drawn on the screen.
    g.headless = bool(_os.environ.get("PLAIN_HEADLESS"))
    if not g.headless:
        import tkinter
        try:
            g.root = tkinter.Tk()
        except tkinter.TclError:
            raise _PlainError("I could not open the window.", line)
        g.tk = tkinter
        g.root.title(title)
        g.root.resizable(False, False)
        g.canvas = tkinter.Canvas(g.root, width=w, height=h, bg="#ffffff", highlightthickness=0, bd=0)
        g.canvas.pack()

        def close():
            g.open = False
            g.root.destroy()

        def moved(e):
            g.mouse[:] = [e.x, e.y]

        def button(state):
            def handler(e):
                g.down = state
                g.mouse[:] = [e.x, e.y]
            return handler

        g.root.protocol("WM_DELETE_WINDOW", close)
        g.root.bind("<KeyPress>", lambda e: g.keys.add(e.keysym.lower()))
        g.root.bind("<KeyRelease>", lambda e: g.keys.discard(e.keysym.lower()))
        g.canvas.bind("<Motion>", moved)
        g.canvas.bind("<ButtonPress-1>", button(True))
        g.canvas.bind("<ButtonRelease-1>", button(False))
        g.root.focus_force()
    _window = g


def window_color(r, g, b, line):
    global _window_color_hex

    def part(v):
        return max(0, min(255, int(v)))
    _window_color_hex = "#%02x%02x%02x" % (part(r), part(g), part(b))
    if _window is not None:
        _window.color = _window_color_hex


def _window_draw(line, action):
    g = _need_window(line)
    if g.open and g.canvas is not None:
        try:
            action(g)
        except g.tk.TclError:
            g.open = False


def window_clear(line):
    def action(g):
        g.canvas.delete("all")
        g.canvas.configure(bg=g.color)
    _window_draw(line, action)


def window_clear_with(r, g, b, line):
    window_color(r, g, b, line)
    window_clear(line)


def window_rectangle(x, y, w, h, line):
    _window_draw(line, lambda g: g.canvas.create_rectangle(int(x), int(y), int(x) + int(w) - 1,
                                                           int(y) + int(h) - 1, fill=g.color, width=0))


def window_circle(x, y, r, line):
    _window_draw(line, lambda g: g.canvas.create_oval(int(x) - int(r), int(y) - int(r), int(x) + int(r),
                                                      int(y) + int(r), fill=g.color, width=0))


def window_line(x1, y1, x2, y2, line):
    _window_draw(line, lambda g: g.canvas.create_line(int(x1), int(y1), int(x2), int(y2), fill=g.color, width=2))


def window_text(text, x, y, line):
    _window_draw(line, lambda g: g.canvas.create_text(int(x), int(y), anchor="nw", text=text, fill=g.color,
                                                      font=("Segoe UI", -20)))


def window_show(line):
    g = _need_window(line)
    if g.open and g.root is not None:
        try:
            g.root.update()
        except g.tk.TclError:
            g.open = False
        _time.sleep(0.015)


def window_is_open(line):
    return _need_window(line).open


def window_close(line):
    g = _need_window(line)
    if g.open:
        g.open = False
        if g.root is not None:
            try:
                g.root.destroy()
            except g.tk.TclError:
                pass


def window_key_pressed(name, line):
    g = _need_window(line)
    if name in _KEYS:
        wanted = _KEYS[name]
    elif len(name) == 1 and name.isalnum() and name.isascii():
        wanted = (name.lower(),)
    else:
        raise _PlainError("I do not know that key. Use left, right, up, down, space, enter, escape, shift, "
                          "ctrl, tab, backspace, a-z or 0-9.", line)
    return g.open and any(k in g.keys for k in wanted)


def window_mouse_x(line):
    return float(_need_window(line).mouse[0])


def window_mouse_y(line):
    return float(_need_window(line).mouse[1])


def window_mouse_down(line):
    g = _need_window(line)
    return g.down and g.open


def _window_finish():
    """When the program ends while the window is still open, keep it on screen until it is closed."""
    g = _window
    if g is not None and g.open and g.root is not None:
        try:
            g.root.mainloop()
        except g.tk.TclError:
            pass


_FINISHERS.append(_window_finish)
