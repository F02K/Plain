"""Small pictures drawn in code (no image files), for the Explorer, the toolbar and the activity bar."""

import math
import tkinter as tk


class Pixels:
    """A tiny drawing board: set pixels, then turn it into an image."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cells = {}

    def dot(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cells[(int(x), int(y))] = color

    def rect(self, x, y, w, h, color, fill=False):
        for i in range(w):
            for j in range(h):
                if fill or i in (0, w - 1) or j in (0, h - 1):
                    self.dot(x + i, y + j, color)

    def line(self, x1, y1, x2, y2, color):
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for i in range(steps + 1):
            self.dot(round(x1 + (x2 - x1) * i / steps), round(y1 + (y2 - y1) * i / steps), color)

    def image(self, master):
        img = tk.PhotoImage(master=master, width=self.w, height=self.h)
        for (x, y), color in self.cells.items():
            img.put(color, (x, y))
        return img


# ---- file types (the same in the dark and the light theme) -------------------------------

PAGE, PAGE_EDGE = "#f0f0f0", "#8a8a8a"
FOLDER, FOLDER_EDGE = "#dcb67a", "#b8934f"
PLAIN_BLUE, PROJECT_ORANGE, MAIN_GREEN = "#4a9eff", "#e8a33d", "#3fb950"


def _page(p, edge=PAGE_EDGE, fill=PAGE):
    p.rect(3, 1, 10, 14, fill, fill=True)
    p.rect(3, 1, 10, 14, edge)
    p.line(10, 1, 12, 3, edge)
    p.line(10, 1, 10, 3, edge)
    p.line(10, 3, 12, 3, edge)


def folder_icon(master, opened=False):
    p = Pixels(16, 16)
    p.rect(1, 3, 6, 3, FOLDER_EDGE, fill=True)
    p.rect(1, 5, 14, 9, FOLDER, fill=True)
    p.rect(1, 5, 14, 9, FOLDER_EDGE)
    if opened:
        p.rect(2, 8, 13, 6, "#f0d29b", fill=True)
        p.rect(2, 8, 13, 6, FOLDER_EDGE)
    return p.image(master)


def file_icon(master):
    p = Pixels(16, 16)
    _page(p)
    return p.image(master)


def plain_icon(master, main=False):
    p = Pixels(16, 16)
    _page(p)
    for y in (6, 8, 10, 12):
        p.line(5, y, 10 if y != 8 else 8, y, PLAIN_BLUE)
    if main:                                  # a green triangle: this is the main program
        for i in range(5):
            p.line(9, 9 + i, 9 + 5 - i, 9 + i, MAIN_GREEN)
        p.rect(9, 9, 1, 5, MAIN_GREEN, fill=True)
    return p.image(master)


def project_icon(master):
    p = Pixels(16, 16)
    _page(p, edge="#a06a10", fill="#fff4dc")
    p.rect(6, 6, 5, 5, PROJECT_ORANGE, fill=True)
    p.rect(7, 7, 3, 3, "#fff4dc", fill=True)
    for x, y in ((8, 5), (8, 11), (5, 8), (11, 8)):
        p.dot(x, y, PROJECT_ORANGE)
    return p.image(master)


# ---- actions (drawn in the text color of the theme) ------------------------------------------

def new_file_icon(master, color):
    p = Pixels(16, 16)
    p.rect(3, 1, 8, 13, color)
    p.line(7, 1, 10, 4, color)
    p.line(7, 1, 7, 4, color)
    p.line(7, 4, 10, 4, color)
    p.line(11, 9, 15, 9, color)
    p.line(13, 7, 13, 11, color)
    return p.image(master)


def new_folder_icon(master, color):
    p = Pixels(16, 16)
    p.rect(1, 3, 5, 2, color)
    p.rect(1, 4, 11, 9, color)
    p.line(11, 9, 15, 9, color)
    p.line(13, 7, 13, 11, color)
    return p.image(master)


def refresh_icon(master, color):
    p = Pixels(16, 16)
    for degrees in range(30, 330, 5):
        a = math.radians(degrees)
        p.dot(8 + 5 * math.cos(a), 8 - 5 * math.sin(a), color)
        p.dot(8 + 4.4 * math.cos(a), 8 - 4.4 * math.sin(a), color)
    p.line(13, 1, 13, 5, color)             # the arrow head
    p.line(13, 5, 9, 5, color)
    p.line(12, 2, 12, 4, color)
    return p.image(master)


def collapse_icon(master, color):
    p = Pixels(16, 16)
    p.rect(2, 4, 10, 10, color)
    p.rect(5, 1, 9, 3, color)
    p.line(4, 9, 10, 9, color)
    return p.image(master)


def explorer_icon(master, color):
    """Two pages on top of each other (the Explorer button of the activity bar)."""
    p = Pixels(28, 28)
    p.rect(9, 3, 14, 18, color)
    p.line(19, 3, 22, 6, color)
    p.line(19, 3, 19, 6, color)
    p.line(19, 6, 22, 6, color)
    p.rect(5, 8, 14, 18, color)
    return p.image(master)


def values_icon(master, color):
    """A list of lines with dots (the Values button of the activity bar)."""
    p = Pixels(28, 28)
    for y in (7, 13, 19):
        p.rect(5, y - 1, 3, 3, color, fill=True)
        p.line(11, y, 23, y, color)
        p.line(11, y + 1, 23, y + 1, color)
    return p.image(master)


class Icons:
    """All pictures for one theme. Make a new Icons when the theme changes."""

    def __init__(self, theme, master):
        c = theme["fg"]
        self.folder = folder_icon(master)
        self.folder_open = folder_icon(master, opened=True)
        self.file = file_icon(master)
        self.plain = plain_icon(master)
        self.plain_main = plain_icon(master, main=True)
        self.project = project_icon(master)
        self.new_file = new_file_icon(master, c)
        self.new_folder = new_folder_icon(master, c)
        self.refresh = refresh_icon(master, c)
        self.collapse = collapse_icon(master, c)
        self.explorer = explorer_icon(master, theme["activity_fg"])
        self.explorer_active = explorer_icon(master, theme["activity_active"])
        self.values = values_icon(master, theme["activity_fg"])
        self.values_active = values_icon(master, theme["activity_active"])
