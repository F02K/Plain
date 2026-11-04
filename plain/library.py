"""Names and types of the built-in helpers, shared by both backends.

Two forms exist, so Plain code keeps reading like English:
  * 'name of value'   one value:   length of name, round of 2.5
  * 'name(a, b)'      more values: random(1, 6), part(name, 0, 3)
"""

from . import typesys as T

# name -> (argument types, result type)
CALLS = {
    "random": ((T.NUMBER, T.NUMBER), T.NUMBER),
    "min": ((T.NUMBER, T.NUMBER), T.NUMBER),
    "max": ((T.NUMBER, T.NUMBER), T.NUMBER),
    "part": ((T.TEXT, T.NUMBER, T.NUMBER), T.TEXT),
    "contains": ((T.TEXT, T.TEXT), T.BOOLEAN),
}

# name -> (argument type, result type)
OF = {
    "length": (T.TEXT, T.NUMBER),
    "upper": (T.TEXT, T.TEXT),
    "lower": (T.TEXT, T.TEXT),
    "round": (T.NUMBER, T.NUMBER),
    "abs": (T.NUMBER, T.NUMBER),
    "sqrt": (T.NUMBER, T.NUMBER),
}

EXAMPLES = {
    "random": "random(1, 6)",
    "min": "min(3, 8)",
    "max": "max(3, 8)",
    "part": 'part("Hello", 0, 2)',
    "contains": 'contains("Hello", "ell") or contains(scores, 10)',
}

# Calls that can fail at run time get the line number as an extra last argument.
NEEDS_LINE = ("random", "part")

# Windows and drawing. All coordinates are numbers, (0, 0) is the top left corner of the window.
GFX = {
    "window": ((T.TEXT, T.NUMBER, T.NUMBER), T.NOTHING),
    "color": ((T.NUMBER, T.NUMBER, T.NUMBER), T.NOTHING),
    "clear": ((), T.NOTHING),
    "rectangle": ((T.NUMBER, T.NUMBER, T.NUMBER, T.NUMBER), T.NOTHING),
    "circle": ((T.NUMBER, T.NUMBER, T.NUMBER), T.NOTHING),
    "line": ((T.NUMBER, T.NUMBER, T.NUMBER, T.NUMBER), T.NOTHING),
    "write": ((T.TEXT, T.NUMBER, T.NUMBER), T.NOTHING),
    "show": ((), T.NOTHING),
    "close_window": ((), T.NOTHING),
    "running": ((), T.BOOLEAN),
    "pressed": ((T.TEXT,), T.BOOLEAN),
    "mouse_x": ((), T.NUMBER),
    "mouse_y": ((), T.NUMBER),
    "mouse_down": ((), T.BOOLEAN),
}
CALLS.update(GFX)
EXAMPLES.update({
    "window": 'window("My game", 640, 480)',
    "color": "color(255, 0, 0)",
    "clear": "clear()",
    "rectangle": "rectangle(10, 10, 100, 50)",
    "circle": "circle(200, 150, 30)",
    "line": "line(0, 0, 100, 100)",
    "write": 'write("Score: 3", 10, 10)',
    "show": "show()",
    "close_window": "close_window()",
    "running": "running()",
    "pressed": 'pressed("left")',
    "mouse_x": "mouse_x()",
    "mouse_y": "mouse_y()",
    "mouse_down": "mouse_down()",
})
