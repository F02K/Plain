"""Plain IDE: a small editor for Plain programs.

Tabs for several files, a project folder on the left, auto completion, a Run
button with an output panel, and a crash handler that keeps your work safe.
It needs nothing but Python (tkinter is part of it), so it works on school computers.

    python ide/plain_ide.py [file.plain ...]

Programs run in a separate process, so the Stop button always works, even for
a program that never ends. The same file is used as the program that runs the
translated code (see run_program_file), so the packaged IDE needs no Python.
"""

import codecs
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)
ROOT = getattr(sys, "_MEIPASS", None) if FROZEN else os.path.dirname(HERE)
if not FROZEN:
    sys.path.insert(0, ROOT)


def run_program_file(path):
    """Child process mode: run a Python file translated from Plain."""
    with open(path, encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, path, "exec"), {"__name__": "__main__"})


if len(sys.argv) >= 3 and sys.argv[1] == "--run":
    run_program_file(sys.argv[2])
    sys.exit(0)

import tkinter as tk  # noqa: E402
from tkinter import filedialog, messagebox, simpledialog, ttk  # noqa: E402
from tkinter import font as tkfont  # noqa: E402

from plain.errors import PlainError, format_error  # noqa: E402
from plain.lexer import KEYWORDS  # noqa: E402
from plain import modules as MODULES  # noqa: E402
from plain.library import CALLS, OF  # noqa: E402
from plain.toolchain import compile_to_python  # noqa: E402

if HERE not in sys.path:
    sys.path.insert(0, HERE)
import projects as PROJECTS  # noqa: E402
from symbols import TOKEN, analyze  # noqa: E402

TITLE = "Plain IDE"
VERSION = "0.2"
NEW_PROGRAM = 'say "Hello, world!"\n'
INDENT = "    "
OPENERS = re.compile(r"\b(then|do|as|times)$")
WORD_BEFORE_CURSOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
HELPER_CALLS = set(CALLS)
HELPERS = HELPER_CALLS | set(OF)
# The sentences of the modules are highlighted as a whole, so that names like 'size' stay ordinary names.
PHRASES = re.compile(MODULES.highlight_regex() + r'|\btakes(?=\s*\()|\bkey(?= (?:"[^"\n]*"|\w+) is pressed)')
COLOR_WORD = re.compile(r"(?<=color )(?:" + "|".join(MODULES.color_names()) + r")\b")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Words that expand into a whole block when you accept them in the completion list.
# {i} is the indentation of the current line, | marks where the cursor ends up.
SNIPPETS = {
    "if": "if | then\n{i}    \n{i}end",
    "while": "while | do\n{i}    \n{i}end",
    "repeat": "repeat | times\n{i}    \n{i}end",
    "for": "for each | in  do\n{i}    \n{i}end",
    "action": "action |name takes() do\n{i}    \n{i}end",
    "define": "define |Name as\n{i}    field as number\n{i}end",
    "try": "try\n{i}    |\n{i}catch error then\n{i}    \n{i}end",
}

for _module in MODULES.load_all():      # 'open', 'draw', 'use', ... fill in a whole sentence
    for _pattern in _module.commands():
        SNIPPETS.setdefault(_pattern.parts[0].word, _pattern.snippet())

# Colors follow Visual Studio Code: "Dark+" and "Light+".
DARK = {
    "bg": "#1e1e1e", "fg": "#d4d4d4", "gutter_bg": "#1e1e1e", "gutter_fg": "#858585",
    "keyword": "#569cd6", "helper": "#c586c0", "string": "#ce9178", "number": "#b5cea8",
    "comment": "#6a9955", "error_line": "#5a1d1d", "current_line": "#282828", "select_bg": "#264f78",
    "out_err": "#f48771", "out_in": "#4fc1ff", "out_info": "#9d9d9d",
    "pop_bg": "#252526", "pop_sel": "#04395e",
    "symbol": "#3a3d41", "symbol_def": "#575c66", "watch_changed": "#4d4a1f",
    "inline_fg": "#7aa2d6", "inline_bg": "#232b3a",
    "ui_bg": "#252526", "toolbar_bg": "#333333", "side_bg": "#252526", "panel_bg": "#1e1e1e",
    "tab_bg": "#2d2d2d", "border": "#3c3c3c", "input_bg": "#3c3c3c",
    "button_bg": "#3c3c3c", "button_hover": "#505050", "accent": "#007acc",
    "run_bg": "#2e7d32", "run_hover": "#388e3c", "scroll": "#424242", "scroll_hover": "#686868",
    "status_bg": "#007acc", "status_fg": "#ffffff", "busy_bg": "#cc6633",
}

LIGHT = {
    "bg": "#ffffff", "fg": "#1f1f1f", "gutter_bg": "#ffffff", "gutter_fg": "#237893",
    "keyword": "#0000ff", "helper": "#af00db", "string": "#a31515", "number": "#098658",
    "comment": "#008000", "error_line": "#ffd9d9", "current_line": "#f3f3f3", "select_bg": "#add6ff",
    "out_err": "#c62828", "out_in": "#0451a5", "out_info": "#6b6b6b",
    "pop_bg": "#f3f3f3", "pop_sel": "#cce4f7",
    "symbol": "#e8e8e8", "symbol_def": "#cfd6e4", "watch_changed": "#fff1b8",
    "inline_fg": "#4a5d86", "inline_bg": "#eef2fb",
    "ui_bg": "#f3f3f3", "toolbar_bg": "#e6e6e6", "side_bg": "#f3f3f3", "panel_bg": "#ffffff",
    "tab_bg": "#ececec", "border": "#d4d4d4", "input_bg": "#ffffff",
    "button_bg": "#dcdcdc", "button_hover": "#c8c8c8", "accent": "#007acc",
    "run_bg": "#2e7d32", "run_hover": "#388e3c", "scroll": "#c1c1c1", "scroll_hover": "#a0a0a0",
    "status_bg": "#007acc", "status_fg": "#ffffff", "busy_bg": "#cc6633",
}

THEMES = {"Dark": DARK, "Light": LIGHT}

CHEAT_SHEET = """\
Variables        let health be 100          set health to health - 5
Output / input   say "Hello"                let name be input "Name?"
                 let age be input number "Age?"
Decisions        if x > 3 then ... else if ... then ... else ... end
Loops            repeat 3 times ... end     while x > 0 do ... end
                 for each item in items do ... end      stop / skip
Actions          action add takes(a, b) do  return a + b  end      do add(1, 2)   or   let n be add(1, 2)
                 action greet do ... end                           do greet()
Things           define Player as  x as number  end
                 let p be Player(x: 0)      say x of p
Lists            let l be list of number    add 5 to l     remove 5 from l
                 remove at 0 from l         sort l         size of l
                 l at 0                     set l at 0 to 7
                 contains(l, 5)
Text helpers     length of t   upper of t   lower of t
                 part(t, 0, 3)              contains(t, "a")
Number helpers   round of x    abs of x     sqrt of x
                 min(a, b)     max(a, b)    random(1, 6)
Windows          open window "Title" with width 640 and height 480
                 while window is open do ... show window ... end     close window
                 use color orange           use color 255, 128, 0    clear window with color black
                 draw rectangle at x, y size w by h      draw circle at x, y radius r
                 draw line from x1, y1 to x2, y2         draw text "hi" at x, y
                 key "left" is pressed      mouse x   mouse y   mouse is down
Colors           red green blue yellow orange purple pink brown gray white black
                 let sky be Color(red: 20, green: 24, blue: 40)    use color sky
Errors           try ... catch error then ... end
Comments         note: this is a comment

In the editor    F5 run, Shift+F5 stop, Ctrl+Space complete, Tab/Enter accept a suggestion
                 Ctrl+N new tab, Ctrl+W close tab, Ctrl+Tab next tab, Ctrl+O open, Ctrl+S save
                 'if', 'while', 'repeat', 'for', 'action', 'define' and 'try' fill in a whole block
Projects         Build (F6) makes a Python file, Release (F7) makes a program (exe) from it
                 File > New project / Open project / Open recent project; the first Save makes a project
Understanding    click a name to see where it is created and used (Ctrl+click jumps to where it is created)
                 'Live values' (next to Run) shows the values behind your code while the program runs; 'Value list' lists them
"""


# ---- crash handling --------------------------------------------------------------

DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share"), "PlainIDE")
LOG_PATH = os.path.join(DATA_DIR, "crash.log")
RECOVERY_DIR = os.path.join(DATA_DIR, "recovery")


def log_crash(where, exc_type, exc, tb):
    """Append a crash report to the log file. Never raises."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')}  Plain IDE {VERSION}  in {where}\n")
            f.write(f"Python {platform.python_version()}  {platform.platform()}  frozen={FROZEN}\n")
            f.write("".join(traceback.format_exception(exc_type, exc, tb)))
            f.write("\n")
        return True
    except OSError:
        return False


def open_folder(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


# ---- running programs ------------------------------------------------------------

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except OSError:
        pass


def apply_styles(root, t, ui_font):
    """Give every ttk widget the look of the theme (flat, like Visual Studio Code)."""
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=t["ui_bg"])
    s.configure(".", background=t["ui_bg"], foreground=t["fg"], fieldbackground=t["input_bg"],
                bordercolor=t["border"], darkcolor=t["ui_bg"], lightcolor=t["ui_bg"], troughcolor=t["bg"],
                focuscolor=t["ui_bg"], selectbackground=t["select_bg"], selectforeground=t["fg"],
                insertcolor=t["fg"], font=ui_font)

    s.configure("TFrame", background=t["ui_bg"])
    s.configure("Toolbar.TFrame", background=t["toolbar_bg"])
    s.configure("Side.TFrame", background=t["side_bg"])
    s.configure("Panel.TFrame", background=t["panel_bg"])
    s.configure("PanelHead.TFrame", background=t["panel_bg"])
    s.configure("Status.TFrame", background=t["status_bg"])
    s.configure("StatusBusy.TFrame", background=t["busy_bg"])

    s.configure("TLabel", background=t["ui_bg"], foreground=t["fg"])
    s.configure("Side.TLabel", background=t["side_bg"], foreground=t["fg"])
    s.configure("SideHead.TLabel", background=t["side_bg"], foreground=t["out_info"], font=(ui_font[0], 8, "bold"))
    s.configure("SideTitle.TLabel", background=t["side_bg"], foreground=t["fg"], font=(ui_font[0], 9, "bold"))
    s.configure("Info.TLabel", background=t["tab_bg"], foreground=t["out_info"])
    s.configure("PanelTitle.TLabel", background=t["panel_bg"], foreground=t["fg"], font=(ui_font[0], 8, "bold"))
    s.configure("Panel.TLabel", background=t["panel_bg"], foreground=t["out_info"])
    s.configure("Status.TLabel", background=t["status_bg"], foreground=t["status_fg"], padding=(10, 2))
    s.configure("StatusBusy.TLabel", background=t["busy_bg"], foreground=t["status_fg"], padding=(10, 2))

    flat = dict(relief="flat", borderwidth=0, focusthickness=0)
    s.configure("TButton", background=t["button_bg"], foreground=t["fg"], padding=(12, 5), **flat)
    s.map("TButton", background=[("disabled", t["button_bg"]), ("pressed", t["button_hover"]),
                                 ("active", t["button_hover"])],
          foreground=[("disabled", t["out_info"])])
    s.configure("Tool.TButton", background=t["button_bg"], foreground=t["fg"], padding=(11, 4), **flat)
    s.map("Tool.TButton", background=[("disabled", t["toolbar_bg"]), ("pressed", t["button_hover"]),
                                      ("active", t["button_hover"])],
          foreground=[("disabled", t["out_info"])])
    s.configure("Run.TButton", background=t["run_bg"], foreground="#ffffff", padding=(14, 4), **flat)
    s.map("Run.TButton", background=[("disabled", t["button_bg"]), ("pressed", t["run_hover"]),
                                     ("active", t["run_hover"])],
          foreground=[("disabled", t["out_info"])])
    s.configure("Toolbar.TCheckbutton", background=t["toolbar_bg"], foreground=t["fg"], padding=(4, 2))
    s.map("Toolbar.TCheckbutton", background=[("active", t["toolbar_bg"])],
          indicatorcolor=[("selected", t["accent"]), ("!selected", t["input_bg"])])
    s.configure("TSeparator", background=t["border"])

    s.configure("TNotebook", background=t["tab_bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    s.configure("TNotebook.Tab", background=t["tab_bg"], foreground=t["out_info"], padding=(16, 7),
                borderwidth=0, lightcolor=t["tab_bg"], bordercolor=t["tab_bg"], darkcolor=t["tab_bg"])
    s.map("TNotebook.Tab", background=[("selected", t["bg"]), ("active", t["button_bg"])],
          foreground=[("selected", t["fg"])], lightcolor=[("selected", t["accent"])],
          bordercolor=[("selected", t["bg"])], darkcolor=[("selected", t["bg"])],
          expand=[("selected", (0, 0, 0, 0))])

    s.configure("Treeview", background=t["side_bg"], fieldbackground=t["side_bg"], foreground=t["fg"],
                borderwidth=0, rowheight=24)
    s.map("Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["fg"])])
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.configure("Treeview.Heading", background=t["tab_bg"], foreground=t["out_info"], relief="flat",
                borderwidth=0, padding=(6, 4))
    s.map("Treeview.Heading", background=[("active", t["tab_bg"])])

    for orient in ("Vertical", "Horizontal"):
        name = f"{orient}.TScrollbar"
        thumb = f"{orient}.Scrollbar.thumb"
        side = "ns" if orient == "Vertical" else "ew"
        s.layout(name, [(f"{orient}.Scrollbar.trough", {"children": [(thumb, {"expand": "1", "sticky": "nswe"})],
                                                         "sticky": side})])
        s.configure(name, background=t["scroll"], troughcolor=t["bg"], bordercolor=t["bg"], relief="flat",
                    borderwidth=0, width=12)
        s.map(name, background=[("active", t["scroll_hover"]), ("pressed", t["scroll_hover"])])

    s.configure("TEntry", fieldbackground=t["input_bg"], foreground=t["fg"], bordercolor=t["border"],
                insertcolor=t["fg"], padding=4)
    s.map("TEntry", bordercolor=[("focus", t["accent"])])
    s.configure("TCombobox", fieldbackground=t["input_bg"], background=t["button_bg"], foreground=t["fg"],
                arrowcolor=t["fg"], bordercolor=t["border"], padding=4)
    s.map("TCombobox", fieldbackground=[("readonly", t["input_bg"])], foreground=[("readonly", t["fg"])],
          selectbackground=[("readonly", t["input_bg"])], selectforeground=[("readonly", t["fg"])])
    root.option_add("*TCombobox*Listbox.background", t["input_bg"])
    root.option_add("*TCombobox*Listbox.foreground", t["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", t["select_bg"])
    root.option_add("*TCombobox*Listbox.selectForeground", t["fg"])
    s.configure("TPanedwindow", background=t["border"])
    s.configure("Sash", sashthickness=3, gripcount=0, background=t["border"])


class Runner:
    """Starts a program in its own process and streams its output."""

    def __init__(self):
        self.proc = None
        self.events = queue.Queue()

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd, extra_env=None):
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", **(extra_env or {}))
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, bufsize=0, env=env,
                                     creationflags=NO_WINDOW)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc):
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while True:
            try:
                data = os.read(proc.stdout.fileno(), 4096)
            except OSError:
                break
            if not data:
                break
            self.events.put((proc, "out", decoder.decode(data).replace("\r", "")))
        self.events.put((proc, "exit", proc.wait()))

    def send(self, line):
        try:
            self.proc.stdin.write((line + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except (OSError, ValueError, AttributeError):
            pass

    def stop(self):
        if self.running:
            self.proc.kill()


# ---- auto completion -------------------------------------------------------------

class Completer:
    """The suggestion list that appears while you type."""

    def __init__(self, tab):
        self.tab = tab
        self.win = None
        self.box = None
        self.matches = []
        self.prefix = ""

    @property
    def visible(self):
        return self.win is not None

    def prefix_at_cursor(self):
        before = self.tab.text.get("insert linestart", "insert")
        m = WORD_BEFORE_CURSOR.search(before)
        return m.group() if m else ""

    def candidates(self, prefix):
        words = set(KEYWORDS) | HELPERS | set(SNIPPETS)
        for m in TOKEN.finditer(self.tab.text.get("1.0", "end-1c")):
            if m.lastgroup == "word":
                words.add(m.group())
        low = prefix.lower()
        found = [w for w in words if w.lower().startswith(low) and w != prefix]
        found.sort(key=lambda w: (w not in KEYWORDS and w not in HELPERS and w not in SNIPPETS, w.lower()))
        return found[:12]

    def update(self, force=False):
        prefix = self.prefix_at_cursor()
        if len(prefix) < (1 if force else 2):
            self.hide()
            return
        matches = self.candidates(prefix)
        if not matches:
            self.hide()
            return
        self.prefix, self.matches = prefix, matches
        self.show()

    def show(self):
        text = self.tab.text
        bbox = text.bbox("insert")
        if not bbox:
            self.hide()
            return
        if not self.win:
            colours = self.tab.app.theme
            self.win = tk.Toplevel(text)
            self.win.wm_overrideredirect(True)
            self.box = tk.Listbox(self.win, font=self.tab.app.font, bd=1, relief="solid", activestyle="none",
                                  exportselection=False, bg=colours["pop_bg"], fg=colours["fg"],
                                  selectbackground=colours["pop_sel"], selectforeground=colours["fg"])
            self.box.pack()
            self.box.bind("<ButtonRelease-1>", self.on_click)
        self.box.delete(0, "end")
        for word in self.matches:
            self.box.insert("end", word)
        self.box.config(height=len(self.matches), width=max(12, max(len(w) for w in self.matches) + 2))
        self.box.selection_clear(0, "end")
        self.box.selection_set(0)
        x, y, _w, h = bbox
        self.win.wm_geometry(f"+{text.winfo_rootx() + x}+{text.winfo_rooty() + y + h}")

    def hide(self):
        if self.win:
            self.win.destroy()
            self.win = self.box = None

    def move(self, delta):
        current = self.box.curselection()[0] if self.box.curselection() else 0
        new = max(0, min(len(self.matches) - 1, current + delta))
        self.box.selection_clear(0, "end")
        self.box.selection_set(new)
        self.box.see(new)

    def on_click(self, _event):
        self.accept()
        self.tab.text.focus_set()

    def accept(self):
        if not self.visible or not self.box.curselection():
            return False
        word = self.matches[self.box.curselection()[0]]
        self.hide()
        text = self.tab.text
        text.delete(f"insert-{len(self.prefix)}c", "insert")
        line_before = text.get("insert linestart", "insert")
        if word in SNIPPETS and not line_before.strip():
            template = SNIPPETS[word].format(i=line_before)
            cursor = template.index("|")
            start = text.index("insert")
            text.insert("insert", template.replace("|", "", 1))
            text.mark_set("insert", f"{start}+{cursor}c")
            return True
        suffix = "(" if word in HELPER_CALLS else " of " if word in OF else ""
        text.insert("insert", word + suffix)
        return True


# ---- one editor tab --------------------------------------------------------------

class EditorTab(ttk.Frame):
    def __init__(self, app, path=None, content=NEW_PROGRAM):
        super().__init__(app.notebook)
        self.app = app
        self.path = path
        self.dirty = False
        self.highlight_job = None
        self.symbol_job = None
        self.inline = {}          # line number -> text shown behind the code while the program runs
        self.inline_labels = {}
        self.line_count = 0
        self.untitled = None
        if path is None:
            app.untitled_count += 1
            self.untitled = f"Untitled {app.untitled_count}"
        font = app.font

        self.gutter = tk.Text(self, width=4, padx=10, pady=6, font=font, bd=0, highlightthickness=0,
                              state="disabled", cursor="arrow", takefocus=0, wrap="none", spacing1=1, spacing3=1)
        self.gutter.tag_configure("right", justify="right")
        self.text = tk.Text(self, font=font, undo=True, wrap="none", bd=0, highlightthickness=0, padx=8, pady=6,
                            tabs=(font.measure(INDENT),), spacing1=1, spacing3=1)
        self.yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.config(yscrollcommand=self.on_yscroll,
                         xscrollcommand=lambda a, b: (xscroll.set(a, b), self.refresh_inline()))
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.yscroll.grid(row=0, column=2, sticky="ns")
        xscroll.grid(row=1, column=1, sticky="ew")
        self.info = ttk.Label(self, text="", anchor="w", padding=(12, 3), style="Info.TLabel")
        self.info.grid(row=2, column=0, columnspan=3, sticky="ew")

        self.restyle()
        self.text.tag_lower("current_line")
        self.text.tag_lower("symbol")
        self.text.tag_lower("symbol_def")
        self.text.tag_raise("sel")

        self.completer = Completer(self)
        self.text.bind("<<Modified>>", self.on_modified)
        self.text.bind("<Return>", self.on_return)
        self.text.bind("<Tab>", self.on_tab)
        self.text.bind("<Up>", lambda e: self.on_arrow(-1))
        self.text.bind("<Down>", lambda e: self.on_arrow(1))
        self.text.bind("<Escape>", lambda e: self.completer.hide())
        for key in ("<Left>", "<Right>", "<Home>", "<End>", "<Prior>", "<Next>"):
            self.text.bind(key, lambda e: self.completer.hide(), add="+")
        self.text.bind("<Control-space>", lambda e: (self.completer.update(force=True), "break")[1])
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<ButtonRelease-1>", lambda e: (self.completer.hide(), self.clear_marks(), self.schedule_symbol(),
                                                       self.update_cursor()))
        self.text.bind("<Control-Button-1>", self.goto_definition)
        # The text widget has its own Ctrl keys (Ctrl+O opens a new line...), so route ours through it.
        for key, action in (("n", app.new_tab), ("o", app.open_dialog), ("s", app.save), ("S", app.save_as),
                            ("w", app.close_tab), ("Tab", app.next_tab), ("Shift-Tab", lambda: app.next_tab(-1))):
            self.text.bind(f"<Control-{key}>", lambda e, action=action: (action(), "break")[1])
        self.gutter.bind("<MouseWheel>", self.on_wheel)
        self.gutter.bind("<Button-4>", self.on_wheel)
        self.gutter.bind("<Button-5>", self.on_wheel)

        self.set_text(content)

    def restyle(self):
        """Colors from the current theme (called when the tab is made and when the theme changes)."""
        t = self.app.theme
        self.gutter.config(bg=t["gutter_bg"], fg=t["gutter_fg"])
        self.text.config(bg=t["bg"], fg=t["fg"], insertbackground=t["fg"], selectbackground=t["select_bg"],
                         selectforeground=t["fg"], inactiveselectbackground=t["select_bg"])
        for tag in ("keyword", "helper", "string", "number", "comment"):
            self.text.tag_configure(tag, foreground=t[tag])
        self.text.tag_configure("error_line", background=t["error_line"])
        self.text.tag_configure("current_line", background=t["current_line"])
        self.text.tag_configure("symbol", background=t["symbol"])
        self.text.tag_configure("symbol_def", background=t["symbol_def"], underline=True)
        for label in self.inline_labels.values():
            label.config(fg=t["inline_fg"], bg=t["inline_bg"])

    def update_cursor(self):
        """Mark the line of the cursor and tell the status bar where it is."""
        self.text.tag_remove("current_line", "1.0", "end")
        if self.text.tag_ranges("sel"):
            return
        line, col = (int(n) for n in self.text.index("insert").split("."))
        self.text.tag_add("current_line", f"{line}.0", f"{line}.end+1c")
        if self.app.current() is self:
            self.app.update_position(line, col + 1)

    # ---- file state ----------------------------------------------------------

    @property
    def name(self):
        return os.path.basename(self.path) if self.path else self.untitled

    def source(self):
        return self.text.get("1.0", "end-1c")

    def set_text(self, content):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.dirty = False
        self.rehighlight()
        self.update_gutter()
        self.clear_marks()

    def on_modified(self, _event):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        if not self.dirty:
            self.dirty = True
            self.app.tab_changed(self)
        self.update_gutter()
        if self.inline and not self.app.runner.running:
            self.clear_inline()     # the lines may have moved, so the old values no longer fit
        if self.highlight_job:
            self.after_cancel(self.highlight_job)
        self.highlight_job = self.after(120, self.rehighlight)

    # ---- look ----------------------------------------------------------------

    def on_yscroll(self, first, last):
        self.yscroll.set(first, last)
        self.gutter.yview_moveto(first)
        self.refresh_inline()

    # ---- live values behind the code -----------------------------------------

    def set_inline(self, lines):
        changed = {n for n, text in lines.items() if self.inline.get(n) != text}
        self.inline = lines
        self.refresh_inline(changed)

    def clear_inline(self):
        self.inline = {}
        for label in self.inline_labels.values():
            label.destroy()
        self.inline_labels = {}

    def refresh_inline(self, changed=()):
        if not self.inline and not self.inline_labels:
            return
        t = self.app.theme
        try:
            first = int(self.text.index("@0,0").split(".")[0])
            last = int(self.text.index(f"@0,{self.text.winfo_height()}").split(".")[0])
        except (tk.TclError, ValueError):
            return
        small = self.app.small_font
        for n, label in list(self.inline_labels.items()):
            if n not in self.inline or not first <= n <= last:
                label.place_forget()
        for n in range(first, last + 1):
            text = self.inline.get(n)
            box = self.text.bbox(f"{n}.end") if text else None
            if not box:
                continue
            x, y, w, h = box
            label = self.inline_labels.get(n)
            if label is None:
                label = tk.Label(self.text, font=small, fg=t["inline_fg"], bg=t["inline_bg"], padx=6, pady=0,
                                 anchor="w", bd=0)
                self.inline_labels[n] = label
            shown = text.replace("->", "→")
            if label.cget("text") != shown:
                label.config(text=shown)
            label.place(x=x + 18, y=y, height=h)
            if n in changed:
                label.config(bg=t["watch_changed"])
                self.after(700, lambda lb=label: lb.winfo_exists() and lb.config(bg=t["inline_bg"]))

    def on_wheel(self, event):
        step = -1 if (event.num == 4 or getattr(event, "delta", 0) > 0) else 1
        self.text.yview_scroll(step * 3, "units")
        return "break"

    def update_gutter(self):
        count = int(self.text.index("end-1c").split(".")[0])
        if count == self.line_count:
            return
        self.line_count = count
        self.gutter.config(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)), "right")
        self.gutter.config(state="disabled")
        self.gutter.yview_moveto(self.text.yview()[0])

    def rehighlight(self):
        self.highlight_job = None
        for tag in ("keyword", "helper", "string", "number", "comment"):
            self.text.tag_remove(tag, "1.0", "end")
        source = self.source()
        quiet = []  # comments and texts: sentence words inside them stay plain
        for m in TOKEN.finditer(source):
            kind = m.lastgroup
            if kind in ("comment", "string"):
                quiet.append((m.start(), m.end()))
            if kind == "word":
                word = m.group()
                kind = "keyword" if word in KEYWORDS else "helper" if word in HELPERS else None
                if kind is None:
                    continue
            self.text.tag_add(kind, f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for pattern in (PHRASES, COLOR_WORD):
            for m in pattern.finditer(source):
                if not any(a <= m.start() < b for a, b in quiet):
                    self.text.tag_add("helper", f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    def clear_marks(self):
        self.text.tag_remove("error_line", "1.0", "end")

    # ---- understanding a name ------------------------------------------------

    def schedule_symbol(self):
        if self.symbol_job:
            self.after_cancel(self.symbol_job)
        self.symbol_job = self.after(150, self.update_symbol)

    def update_symbol(self):
        """Mark where the name under the cursor is created (strong) and used (light) and explain it."""
        self.symbol_job = None
        for tag in ("symbol", "symbol_def"):
            self.text.tag_remove(tag, "1.0", "end")
        line, col = (int(n) for n in self.text.index("insert").split("."))
        try:
            found = analyze(self.source(), line, col)
        except Exception:  # an explanation must never get in the way of typing
            found = None
        if not found:
            self.info.config(text="")
            return
        self.info.config(text=f"{found['word']}   -   {found['text']}" if found["text"] else "")
        for tag, spans in (("symbol", found["uses"]), ("symbol_def", found["defs"])):
            for a, b in spans:
                self.text.tag_add(tag, f"1.0+{a}c", f"1.0+{b}c")

    def goto_definition(self, event):
        line, col = (int(n) for n in self.text.index(f"@{event.x},{event.y}").split("."))
        found = analyze(self.source(), line, col)
        if found and found["defs"]:
            self.text.mark_set("insert", f"1.0+{found['defs'][0][0]}c")
            self.text.see("insert")
            self.update_symbol()
        return "break"

    def show_name(self, name, line):
        """Used by the value watcher: jump to the line where a value changed and explain the name."""
        text = self.text.get(f"{line}.0", f"{line}.end")
        m = re.search(r"\b" + re.escape(name) + r"\b", text)
        self.text.mark_set("insert", f"{line}.{m.start() if m else 0}")
        self.text.see("insert")
        self.update_symbol()

    def mark_line(self, line):
        if line and line >= 1:
            self.text.tag_add("error_line", f"{line}.0", f"{line}.end+1c")
            self.text.see(f"{line}.0")

    # ---- typing help ---------------------------------------------------------

    def on_return(self, _event):
        if self.completer.visible:
            self.completer.accept()
            return "break"
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r" *", line).group()
        code = re.sub(r"\bnote:.*$", "", line).strip()
        if OPENERS.search(code) or code in ("try", "else"):
            indent += INDENT
        self.text.insert("insert", "\n" + indent)
        self.text.see("insert")
        return "break"

    def on_tab(self, _event):
        if self.completer.visible:
            self.completer.accept()
        else:
            self.text.insert("insert", INDENT)
        return "break"

    def on_arrow(self, delta):
        if self.completer.visible:
            self.completer.move(delta)
            return "break"
        return None

    def on_key_release(self, event):
        key = event.keysym
        self.schedule_symbol()
        self.update_cursor()
        if not (len(key) == 1 and (key.isalnum() or key == "_")) and key not in ("BackSpace", "Delete"):
            return
        # Pull 'end', 'else' and 'catch' back to the level of the block they close.
        line = self.text.get("insert linestart", "insert lineend")
        word = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if word in ("end", "else", "catch") and indent >= len(INDENT) and line.endswith(word) \
                and self.text.index("insert") == self.text.index("insert lineend"):
            self.text.delete("insert linestart", f"insert linestart+{len(INDENT)}c")
        self.completer.update()


# ---- the application -------------------------------------------------------------

class App:
    def __init__(self, root, paths=()):
        self.root = root
        self.theme_name = load_settings().get("theme", "Dark")
        if self.theme_name not in THEMES:
            self.theme_name = "Dark"
        self.theme = THEMES[self.theme_name]
        self.status_text, self.status_busy = "Ready", False
        self.runner = Runner()
        self.tmp = tempfile.mkdtemp(prefix="plain_ide_")
        self.untitled_count = 0
        self.run_id = 0
        self.run_tab = None
        self.project = None             # the folder shown on the left
        self.project_info = None        # its project definition (a .plainproject file), if it has one
        self.build_queue = queue.Queue()
        self.building = False
        self.build_log = []
        self.reporting = False
        self.folder_nodes = {}
        self.watch_var = tk.BooleanVar(value=False)    # the list of values on the right
        self.live_var = tk.BooleanVar(value=False)     # the values behind the code
        self.watch_file = None
        self.watch_seq = 0
        self.watch_rows = {}
        self.watch_changed = {}

        base = tkfont.nametofont("TkFixedFont").copy()
        family = "Consolas" if sys.platform.startswith("win") else base.actual("family")
        self.font = tkfont.Font(family=family, size=13)
        self.small_font = tkfont.Font(family=family, size=10)
        ui_family = "Segoe UI" if sys.platform.startswith("win") else tkfont.nametofont("TkDefaultFont").actual("family")
        self.ui_font = (ui_family, 10)
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(name).configure(family=ui_family, size=10)
        apply_styles(self.root, self.theme, self.ui_font)

        self.build_menu()
        self.build_toolbar()
        self.build_status()
        self.build_panes()
        self.bind_keys()
        self.install_crash_handler()

        self.restore_session()
        for path in paths:
            self.open_path(path)
        if not self.tabs():
            self.new_tab()
        self.tab_changed()
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.after(40, self.poll)
        root.after(200, self.poll_watch)
        root.after(20000, self.autosave)

    # ---- layout --------------------------------------------------------------

    def build_menu(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New tab", accelerator="Ctrl+N", command=self.new_tab)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="New project...", command=self.new_project_dialog)
        file_menu.add_command(label="Open project...", command=self.open_project_file_dialog)
        self.recent_menu = tk.Menu(file_menu, tearoff=False, postcommand=self.fill_recent_menu)
        file_menu.add_cascade(label="Open recent project", menu=self.recent_menu)
        file_menu.add_command(label="Open folder...", command=self.open_project_dialog)
        file_menu.add_command(label="Close project", command=self.close_project)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file_menu.add_command(label="Save as...", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_command(label="Save all", command=self.save_all)
        file_menu.add_separator()
        file_menu.add_command(label="Close tab", accelerator="Ctrl+W", command=self.close_tab)
        file_menu.add_command(label="Exit", command=self.quit)
        menu.add_cascade(label="File", menu=file_menu)

        examples_menu = tk.Menu(menu, tearoff=False)
        examples = os.path.join(ROOT, "examples")
        if os.path.isdir(examples):
            for name in sorted(os.listdir(examples)):
                if name.endswith(".plain"):
                    examples_menu.add_command(label=name[:-6],
                                              command=lambda n=name: self.open_example(os.path.join(examples, n)))
        menu.add_cascade(label="Examples", menu=examples_menu)

        run_menu = tk.Menu(menu, tearoff=False)
        run_menu.add_command(label="Run", accelerator="F5", command=self.run)
        run_menu.add_command(label="Stop", accelerator="Shift+F5", command=self.stop)
        menu.add_cascade(label="Run", menu=run_menu)

        build_menu = tk.Menu(menu, tearoff=False)
        build_menu.add_command(label="Build Python file", accelerator="F6", command=self.build_action)
        build_menu.add_command(label="Release: make a program (exe)", accelerator="F7", command=self.release_action)
        build_menu.add_separator()
        build_menu.add_command(label="Show build folder", command=self.show_build_folder)
        build_menu.add_command(label="Project settings...", command=self.project_settings)
        menu.add_cascade(label="Build", menu=build_menu)

        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Bigger text", accelerator="Ctrl++", command=lambda: self.zoom(1))
        view_menu.add_command(label="Smaller text", accelerator="Ctrl+-", command=lambda: self.zoom(-1))
        view_menu.add_separator()
        self.theme_var = tk.StringVar(value=self.theme_name)
        for name in THEMES:
            view_menu.add_radiobutton(label=f"{name} theme", variable=self.theme_var, value=name,
                                      command=lambda n=name: self.apply_theme(n))
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Live values in the code", variable=self.live_var)
        view_menu.add_checkbutton(label="List of values", variable=self.watch_var, command=self.toggle_watch)
        menu.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Quick reference", accelerator="F1", command=self.show_help)
        help_menu.add_command(label="Open crash log folder", command=lambda: self.open_data_folder())
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def build_toolbar(self):
        bar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(8, 5))
        bar.pack(side="top", fill="x")
        self.run_button = ttk.Button(bar, text="\u25b6  Run  F5", style="Run.TButton", command=self.run)
        self.run_button.pack(side="left")
        self.stop_button = ttk.Button(bar, text="\u25a0  Stop", style="Tool.TButton", command=self.stop,
                                      state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=14, pady=3)
        self.build_button = ttk.Button(bar, text="Build  F6", style="Tool.TButton", command=self.build_action)
        self.build_button.pack(side="left")
        self.release_button = ttk.Button(bar, text="Release  F7", style="Tool.TButton", command=self.release_action)
        self.release_button.pack(side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=14, pady=3)
        ttk.Checkbutton(bar, text="Live values", style="Toolbar.TCheckbutton",
                        variable=self.live_var).pack(side="left")
        ttk.Checkbutton(bar, text="Value list", style="Toolbar.TCheckbutton", variable=self.watch_var,
                        command=self.toggle_watch).pack(side="left", padx=(10, 0))
        ttk.Button(bar, text="Dark / Light", style="Tool.TButton", command=self.toggle_theme).pack(side="right")

    def build_status(self):
        bar = ttk.Frame(self.root, style="Status.TFrame")
        bar.pack(side="bottom", fill="x")
        self.status_frame = bar
        self.status_labels = []
        for text, side in (("Ready", "left"), ("", "left"), ("Plain", "right"), ("Spaces: 4", "right"),
                           ("Ln 1, Col 1", "right")):
            label = ttk.Label(bar, text=text, style="Status.TLabel")
            label.pack(side=side)
            self.status_labels.append(label)
        self.status_left, self.status_project, self.status_lang, self.status_indent, self.status_pos = \
            self.status_labels

    def set_status(self, text, busy=False):
        """The colored bar at the bottom: blue when idle, orange while a program runs or is built."""
        self.status_text, self.status_busy = text, busy
        suffix = "Busy" if busy else ""
        self.status_frame.config(style=f"Status{suffix}.TFrame")
        for label in self.status_labels:
            label.config(style=f"Status{suffix}.TLabel")
        self.status_left.config(text=text)

    def update_position(self, line, col):
        self.status_pos.config(text=f"Ln {line}, Col {col}")

    def update_project_status(self):
        if self.project_info:
            self.status_project.config(text=f"Project: {self.project_info.name}")
        elif self.project:
            self.status_project.config(text=f"Folder: {os.path.basename(self.project) or self.project}")
        else:
            self.status_project.config(text="")

    def toggle_theme(self):
        self.apply_theme("Light" if self.theme_name == "Dark" else "Dark")

    def apply_theme(self, name):
        self.theme_name = name
        self.theme = THEMES[name]
        self.theme_var.set(name)
        save_settings(dict(load_settings(), theme=name))
        t = self.theme
        apply_styles(self.root, t, self.ui_font)
        self.output.config(bg=t["panel_bg"], fg=t["fg"], insertbackground=t["fg"], selectbackground=t["select_bg"],
                           inactiveselectbackground=t["select_bg"])
        self.output.tag_configure("err", foreground=t["out_err"])
        self.output.tag_configure("in", foreground=t["out_in"])
        self.output.tag_configure("info", foreground=t["out_info"])
        self.watch_tree.tag_configure("changed", background=t["watch_changed"])
        for tab in self.tabs():
            tab.restyle()
        self.set_status(self.status_text, self.status_busy)

    def build_panes(self):
        t = self.theme
        self.hpane = ttk.PanedWindow(self.root, orient="horizontal")
        self.hpane.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(self.hpane, style="Side.TFrame")
        ttk.Label(self.sidebar, text="EXPLORER", style="SideHead.TLabel", padding=(12, 8, 6, 2)).grid(
            row=0, column=0, sticky="w")
        ttk.Button(self.sidebar, text="+ File", style="Tool.TButton", command=self.new_project_file).grid(
            row=0, column=1, columnspan=2, sticky="e", padx=6, pady=(6, 2))
        self.project_label = ttk.Label(self.sidebar, text="", style="SideTitle.TLabel", padding=(12, 2, 6, 6))
        self.project_label.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.tree = ttk.Treeview(self.sidebar, show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=tree_scroll.set)
        self.tree.grid(row=2, column=0, columnspan=2, sticky="nsew")
        tree_scroll.grid(row=2, column=2, sticky="ns")
        self.sidebar.rowconfigure(2, weight=1)
        self.sidebar.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self.on_tree_open)
        self.tree.bind("<Return>", self.on_tree_open)

        main = ttk.Frame(self.hpane)
        self.hpane.add(main, weight=1)
        self.editor_split = ttk.PanedWindow(main, orient="horizontal")
        self.editor_split.pack(fill="both", expand=True)
        vpane = ttk.PanedWindow(self.editor_split, orient="vertical")
        self.editor_split.add(vpane, weight=1)

        # The value list on the right: hidden until 'Value list' is switched on.
        self.watch_frame = ttk.Frame(self.editor_split, style="Side.TFrame", width=300)
        ttk.Label(self.watch_frame, text="VALUES", style="SideHead.TLabel", padding=(12, 8, 6, 6)).grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.watch_tree = ttk.Treeview(self.watch_frame, columns=("value", "line"), show="tree headings",
                                       selectmode="browse")
        self.watch_tree.heading("#0", text="Name")
        self.watch_tree.heading("value", text="Value")
        self.watch_tree.heading("line", text="Line")
        self.watch_tree.column("#0", width=110, stretch=False)
        self.watch_tree.column("value", width=170, stretch=True)
        self.watch_tree.column("line", width=40, stretch=False, anchor="e")
        self.watch_tree.tag_configure("changed", background=t["watch_changed"])
        watch_scroll = ttk.Scrollbar(self.watch_frame, orient="vertical", command=self.watch_tree.yview)
        self.watch_tree.config(yscrollcommand=watch_scroll.set)
        self.watch_tree.grid(row=1, column=0, sticky="nsew")
        watch_scroll.grid(row=1, column=1, sticky="ns")
        self.watch_note = ttk.Label(self.watch_frame, text="", padding=(12, 6), wraplength=260, style="Side.TLabel")
        self.watch_note.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.watch_frame.rowconfigure(1, weight=1)
        self.watch_frame.columnconfigure(0, weight=1)
        self.watch_tree.bind("<<TreeviewSelect>>", self.on_watch_select)

        self.notebook = ttk.Notebook(vpane)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.on_tab_switch())
        self.notebook.bind("<ButtonRelease-2>", self.on_tab_middle_click)
        self.notebook.bind("<Button-3>", self.on_tab_right_click)
        vpane.add(self.notebook, weight=3)

        bottom = ttk.Frame(vpane, style="Panel.TFrame")
        head = ttk.Frame(bottom, style="PanelHead.TFrame")
        ttk.Label(head, text="OUTPUT", style="PanelTitle.TLabel", padding=(14, 7, 6, 5)).pack(side="left")
        ttk.Button(head, text="Clear", style="Tool.TButton", command=self.clear_output).pack(
            side="right", padx=8, pady=3)
        head.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.output = tk.Text(bottom, font=self.font, bg=t["panel_bg"], fg=t["fg"], insertbackground=t["fg"],
                              height=9, wrap="word", bd=0, highlightthickness=0, padx=14, pady=6,
                              state="disabled", selectbackground=t["select_bg"],
                              inactiveselectbackground=t["select_bg"])
        out_scroll = ttk.Scrollbar(bottom, orient="vertical", command=self.output.yview)
        self.output.config(yscrollcommand=out_scroll.set)
        self.output.tag_configure("err", foreground=t["out_err"])
        self.output.tag_configure("in", foreground=t["out_in"])
        self.output.tag_configure("info", foreground=t["out_info"])
        entry_row = ttk.Frame(bottom, style="Panel.TFrame", padding=(14, 4, 8, 6))
        ttk.Label(entry_row, text="Input", style="Panel.TLabel").pack(side="left")
        self.entry = ttk.Entry(entry_row, state="disabled")
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.entry.bind("<Return>", self.send_input)
        bottom.rowconfigure(1, weight=1)
        bottom.columnconfigure(0, weight=1)
        self.output.grid(row=1, column=0, sticky="nsew")
        out_scroll.grid(row=1, column=1, sticky="ns")
        entry_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        vpane.add(bottom, weight=1)

        self.tab_menu = tk.Menu(self.root, tearoff=False)
        self.tab_menu.add_command(label="Close tab", command=lambda: self.close_tab(self.menu_tab))
        self.tab_menu.add_command(label="Close other tabs", command=self.close_other_tabs)
        self.menu_tab = None

    def bind_keys(self):
        r = self.root
        r.bind("<F5>", lambda e: self.run())
        r.bind("<Shift-F5>", lambda e: self.stop())
        r.bind("<F6>", lambda e: self.build_action())
        r.bind("<F7>", lambda e: self.release_action())
        r.bind("<F1>", lambda e: self.show_help())
        r.bind("<Control-n>", lambda e: self.new_tab())
        r.bind("<Control-Tab>", lambda e: self.next_tab())
        r.bind("<Control-o>", lambda e: self.open_dialog())
        r.bind("<Control-s>", lambda e: self.save())
        r.bind("<Control-S>", lambda e: self.save_as())
        r.bind("<Control-w>", lambda e: self.close_tab())
        r.bind("<Control-plus>", lambda e: self.zoom(1))
        r.bind("<Control-equal>", lambda e: self.zoom(1))
        r.bind("<Control-minus>", lambda e: self.zoom(-1))

    def zoom(self, delta):
        self.font.configure(size=max(8, min(36, self.font.cget("size") + delta)))
        self.small_font.configure(size=max(7, self.font.cget("size") - 3))
        self.root.after(50, lambda: [tab.refresh_inline() for tab in self.tabs()])

    # ---- tabs ----------------------------------------------------------------

    def tabs(self):
        return [self.root.nametowidget(name) for name in self.notebook.tabs()]

    def current(self):
        name = self.notebook.select()
        return self.root.nametowidget(name) if name else None

    def add_tab(self, tab):
        self.notebook.add(tab, text=tab.name)
        self.notebook.select(tab)
        tab.text.focus_set()
        return tab

    def next_tab(self, step=1):
        tabs = self.tabs()
        if len(tabs) > 1:
            self.notebook.select(tabs[(tabs.index(self.current()) + step) % len(tabs)])

    def new_tab(self, path=None, content=NEW_PROGRAM):
        return self.add_tab(EditorTab(self, path, content))

    def tab_changed(self, tab=None):
        """Refresh tab titles and the window title."""
        for t in self.tabs():
            self.notebook.tab(t, text=("*" if t.dirty else "") + t.name)
        current = self.current()
        if current:
            self.root.title(f"{'*' if current.dirty else ''}{current.name} - {TITLE}")
        self.update_project_status()

    def on_tab_switch(self):
        for t in self.tabs():
            t.completer.hide()
        self.tab_changed()
        if self.current():
            self.current().update_cursor()

    def on_tab_middle_click(self, event):
        index = self.tab_index_at(event)
        if index is not None:
            self.close_tab(self.tabs()[index])

    def on_tab_right_click(self, event):
        index = self.tab_index_at(event)
        if index is not None:
            self.menu_tab = self.tabs()[index]
            self.tab_menu.tk_popup(event.x_root, event.y_root)

    def tab_index_at(self, event):
        try:
            return self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None

    def confirm_save(self, tab):
        """Ask what to do with unsaved changes. Returns False when the user cancels."""
        if not tab.dirty:
            return True
        self.notebook.select(tab)
        answer = messagebox.askyesnocancel(TITLE, f"Save '{tab.name}' before closing?")
        if answer is None:
            return False
        return self.save(tab) if answer else True

    def close_tab(self, tab=None):
        tab = tab or self.current()
        if tab is None or not self.confirm_save(tab):
            return False
        tab.completer.hide()
        self.notebook.forget(tab)
        tab.destroy()
        if self.run_tab is tab:
            self.run_tab = None
        if not self.tabs():
            self.new_tab()
        self.tab_changed()
        return True

    def close_other_tabs(self):
        keep = self.menu_tab
        for tab in self.tabs():
            if tab is not keep and not self.close_tab(tab):
                break

    # ---- files ---------------------------------------------------------------

    def find_tab(self, path):
        full = os.path.normcase(os.path.abspath(path))
        for tab in self.tabs():
            if tab.path and os.path.normcase(os.path.abspath(tab.path)) == full:
                return tab
        return None

    def open_path(self, path):
        if path.endswith(PROJECTS.EXT):
            self.open_project_file(path)
            return None
        existing = self.find_tab(path)
        if existing:
            self.notebook.select(existing)
            return existing
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot open this file: {exc.strerror}")
            return None
        # Replace an untouched empty starter tab instead of keeping it around.
        only = self.tabs()
        tab = self.new_tab(os.path.abspath(path), content)
        if len(only) == 1 and only[0].path is None and not only[0].dirty and only[0].source() == NEW_PROGRAM:
            self.close_tab(only[0])
        self.tab_changed()
        return tab

    def open_dialog(self):
        for path in filedialog.askopenfilenames(filetypes=[("Plain programs", "*.plain"), ("All files", "*.*")]):
            self.open_path(path)

    def open_example(self, path):
        with open(path, encoding="utf-8") as f:
            self.new_tab(None, f.read())

    def save(self, tab=None):
        tab = tab or self.current()
        if tab.path is None:
            return self.save_as(tab)
        return self.write(tab, tab.path)

    def save_as(self, tab=None):
        tab = tab or self.current()
        if tab.path is None and self.project is None:
            # A first save always creates a project, so the program has a home for its builds.
            return self.new_project_dialog(tab)
        options = {"defaultextension": ".plain", "filetypes": [("Plain programs", "*.plain"), ("All files", "*.*")]}
        if self.project:
            options["initialdir"] = self.project
        path = filedialog.asksaveasfilename(**options)
        return bool(path) and self.write(tab, path)

    def save_all(self):
        for tab in self.tabs():
            if tab.dirty and not self.save(tab):
                break

    def write(self, tab, path):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                source = tab.source()
                f.write(source if source.endswith("\n") else source + "\n")
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot save this file: {exc.strerror}")
            return False
        tab.path = os.path.abspath(path)
        tab.dirty = False
        self.tab_changed()
        if self.project:
            self.refresh_tree()
        return True

    def quit(self):
        for tab in self.tabs():
            if not self.confirm_save(tab):
                return
        self.runner.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(RECOVERY_DIR, ignore_errors=True)
        self.root.destroy()

    # ---- projects (a folder of programs) -------------------------------------

    def open_project_dialog(self):
        folder = filedialog.askdirectory(title="Open a folder with Plain programs")
        if folder:
            self.open_project(folder)

    def open_project(self, folder):
        self.project = os.path.abspath(folder)
        self.project_info = PROJECTS.Project.find(self.project)
        if self.project_info:
            PROJECTS.add_recent(DATA_DIR, self.project_info.path)
        self.project_label.config(text=self.project_info.name if self.project_info
                                  else os.path.basename(self.project) or self.project)
        if str(self.sidebar) not in self.hpane.panes():
            self.hpane.insert(0, self.sidebar, weight=0)
            self.root.after(50, lambda: self.hpane.sashpos(0, 210))
        self.refresh_tree()

    def close_project(self):
        self.project = None
        self.project_info = None
        if str(self.sidebar) in self.hpane.panes():
            self.hpane.forget(self.sidebar)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.folder_nodes = {self.project: ""}
        skip = {"__pycache__", "node_modules", "dist", "build"}
        for dirpath, dirs, files in os.walk(self.project):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in skip)
            if dirpath.count(os.sep) - self.project.count(os.sep) >= 4:
                dirs[:] = []
            parent = self.folder_nodes[dirpath]
            for d in dirs:
                full = os.path.join(dirpath, d)
                self.folder_nodes[full] = self.tree.insert(parent, "end", text=d, values=(full, "dir"), open=True)
            for f in sorted(files):
                if f.endswith(".plain"):
                    self.tree.insert(parent, "end", text=f, values=(os.path.join(dirpath, f), "file"))
                elif f.endswith(PROJECTS.EXT):
                    self.tree.insert(parent, "end", text=f, values=(os.path.join(dirpath, f), "project"))

    def on_tree_open(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        path, kind = self.tree.item(selection[0], "values")
        if kind == "file":
            self.open_path(path)
        elif kind == "project":
            self.project_settings()

    def new_project_file(self):
        if not self.project:
            return
        name = simpledialog.askstring(TITLE, "Name of the new program:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name.endswith(".plain"):
            name += ".plain"
        folder = self.project
        selection = self.tree.selection()
        if selection:
            path, kind = self.tree.item(selection[0], "values")
            folder = path if kind == "dir" else os.path.dirname(path)
        target = os.path.join(folder, name)
        if os.path.exists(target):
            messagebox.showerror(TITLE, "A file with this name already exists.")
            return
        try:
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(NEW_PROGRAM)
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot create this file: {exc.strerror}")
            return
        self.refresh_tree()
        self.open_path(target)

    # ---- project files, recent projects ------------------------------------------

    def open_project_file_dialog(self):
        path = filedialog.askopenfilename(title="Open a Plain project",
                                          filetypes=[("Plain projects", "*" + PROJECTS.EXT), ("All files", "*.*")])
        if path:
            self.open_project_file(path)

    def open_project_file(self, path):
        try:
            info = PROJECTS.Project.load(path)
        except ValueError as exc:
            messagebox.showerror(TITLE, str(exc))
            return False
        self.open_project(info.folder)
        if self.project_info is None:       # the file has another name than the one the folder holds
            self.project_info = info
            PROJECTS.add_recent(DATA_DIR, path)
        if os.path.isfile(self.project_info.main_path):
            self.open_path(self.project_info.main_path)
        return True

    def fill_recent_menu(self):
        self.recent_menu.delete(0, "end")
        paths = PROJECTS.recent_projects(DATA_DIR)
        for path in paths:
            label = f"{os.path.splitext(os.path.basename(path))[0]}    ({os.path.dirname(path)})"
            self.recent_menu.add_command(label=label, command=lambda p=path: self.open_project_file(p))
        if paths:
            self.recent_menu.add_separator()
            self.recent_menu.add_command(label="Clear this list", command=lambda: PROJECTS.clear_recent(DATA_DIR))
        else:
            self.recent_menu.add_command(label="(no projects yet)", state="disabled")

    def new_project_dialog(self, tab=None):
        """Make a project in a folder you choose. With a tab: the program in it becomes the main program."""
        folder = filedialog.askdirectory(title="Choose the folder for your project (make a new one if you like)",
                                         mustexist=False)
        if not folder:
            return False
        folder = os.path.abspath(folder)
        os.makedirs(folder, exist_ok=True)
        info = PROJECTS.Project.find(folder)
        if info is None:
            name = os.path.basename(folder) or "program"
            main = "main.plain"
            if tab is not None and tab.path and os.path.dirname(os.path.abspath(tab.path)) == folder:
                main = os.path.basename(tab.path)
            info = PROJECTS.Project(folder, name, main)
            try:
                info.save()
            except OSError as exc:
                messagebox.showerror(TITLE, f"I cannot create the project: {exc.strerror}")
                return False
        if tab is not None and tab.path is None:
            target = info.main_path
            if os.path.exists(target):
                n = 2
                while os.path.exists(os.path.join(folder, f"program{n}.plain")):
                    n += 1
                target = os.path.join(folder, f"program{n}.plain")
            if not self.write(tab, target):
                return False
        elif tab is None and not os.path.exists(info.main_path):
            try:
                with open(info.main_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(NEW_PROGRAM)
            except OSError as exc:
                messagebox.showerror(TITLE, f"I cannot create the program: {exc.strerror}")
                return False
        self.open_project(folder)
        if tab is None and os.path.isfile(info.main_path):
            self.open_path(info.main_path)
        self.write_output(f"Project '{info.name}' is ready in {folder}\n", "info")
        return True

    def project_settings(self):
        info = self.project_info
        if info is None:
            if not self.make_project_here():
                return
            info = self.project_info
        win = tk.Toplevel(self.root)
        win.title(f"Project settings - {info.name}")
        win.transient(self.root)
        win.resizable(False, False)
        win.configure(bg=self.theme["ui_bg"])
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
        ttk.Label(frame, text="The main program is what Build and Release turn into a Python file and a program.",
                  wraplength=380).grid(row=3, column=0, columnspan=2, pady=(8, 0))

        def apply():
            old = info.path
            info.name = name.get().strip() or info.name
            info.main = main.get() or info.main
            info.output = PROJECTS.slug(output.get() or info.name)
            try:
                info.save()
                if info.path != old and os.path.exists(old):
                    os.remove(old)
            except OSError as exc:
                messagebox.showerror(TITLE, f"I cannot save the project: {exc.strerror}", parent=win)
                return
            PROJECTS.add_recent(DATA_DIR, info.path)
            self.project_label.config(text=info.name)
            self.refresh_tree()
            win.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", command=apply).pack(side="right", padx=(0, 8))

    def make_project_here(self):
        """Builds need a project. Turn the open folder into one, or ask for a folder."""
        tab = self.current()
        if self.project is None and tab is not None and tab.path:
            self.open_project(os.path.dirname(os.path.abspath(tab.path)))      # the folder of the program
            if self.project_info:
                return True
        if self.project is None:
            return self.new_project_dialog(tab if tab is not None and tab.path is None else None) \
                and self.project_info is not None
        if not messagebox.askyesno(TITLE, "This folder is not a project yet.\n\nMake it a project, so that the "
                                          "program can be built?"):
            return False
        main = "main.plain"
        if tab is not None and tab.path and os.path.dirname(os.path.abspath(tab.path)) == self.project:
            main = os.path.basename(tab.path)
        elif not os.path.exists(os.path.join(self.project, main)) and self.project_files():
            main = self.project_files()[0]
        info = PROJECTS.Project(self.project, os.path.basename(self.project), main)
        try:
            info.save()
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot create the project: {exc.strerror}")
            return False
        self.open_project(self.project)
        return True

    def project_files(self):
        return PROJECTS.Project(self.project).plain_files() if self.project else []

    # ---- building ------------------------------------------------------------

    def save_project_tabs(self):
        for tab in self.tabs():
            if tab.dirty and tab.path and not self.save(tab):
                return False
        return True

    def need_project(self):
        if self.building:
            return None
        if self.project_info is None and not self.make_project_here():
            return None
        info = self.project_info
        if info is None:
            return None
        tab = self.current()
        if tab is not None and tab.path is None and not info.plain_files():
            self.save(tab)
        if not self.save_project_tabs():
            return None
        if not os.path.isfile(info.main_path):
            messagebox.showerror(TITLE, f"The main program '{info.main}' does not exist.\n\n"
                                        "Choose another one in Build > Project settings.")
            return None
        return info

    def build_action(self, quiet=False):
        """Translate the main program to a Python file. Returns the modules it uses, or None on a mistake."""
        info = self.need_project()
        if info is None:
            return None
        self.clear_output()
        for t in self.tabs():
            t.clear_marks()
        try:
            path, imports = PROJECTS.build_python(info)
        except PlainError as err:
            with open(info.main_path, encoding="utf-8") as f:
                source = f.read()
            self.write_output(format_error(err, source, info.main) + "\n", "err")
            tab = self.find_tab(info.main_path)
            if tab:
                tab.mark_line(err.line)
            return None
        except OSError as exc:
            self.write_output(f"I cannot build the program: {exc.strerror}\n", "err")
            return None
        relative = os.path.relpath(path, info.folder)
        self.write_output(f"Built {relative}\nRun it anywhere with Python 3.10 or newer:  python {relative}\n", "info")
        return imports

    def release_action(self):
        imports = self.build_action()
        if imports is None:
            return
        info = self.project_info
        self.write_output("\nMaking the program (an exe needs Python and PyInstaller on this computer)...\n", "info")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            python, has_pyinstaller = PROJECTS.find_python()
        finally:
            self.root.config(cursor="")
        if python is None:
            self.write_output("I could not find Python 3.10 or newer on this computer.\n"
                              "Install it from python.org, then try Release again. "
                              "The Python file from Build works without this step.\n", "err")
            return
        steps = []
        if not has_pyinstaller:
            if not messagebox.askyesno(TITLE, "To make a program I need PyInstaller.\n\n"
                                              "Install it now? (pip install pyinstaller)"):
                self.write_output("Stopped: PyInstaller is not installed.\n", "err")
                return
            steps.append(python + ["-m", "pip", "install", "pyinstaller"])
        steps.append(python + PROJECTS.pyinstaller_arguments(info, "window" in imports))
        self.set_building(True)
        self.build_log = []
        self.write_output("Working... this takes a minute.\n", "info")
        threading.Thread(target=self.run_build_steps, args=(steps,), daemon=True).start()

    def run_build_steps(self, steps):
        """Runs in a thread: the output is passed on through build_queue."""
        for command in steps:
            try:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=NO_WINDOW)
                for raw in proc.stdout:
                    self.build_queue.put(("line", raw.decode("utf-8", "replace").rstrip()))
                code = proc.wait()
            except OSError as exc:
                self.build_queue.put(("line", str(exc)))
                code = 1
            if code != 0:
                self.build_queue.put(("done", code))
                return
        self.build_queue.put(("done", 0))

    def set_building(self, building):
        self.building = building
        self.set_status("Building..." if building else "Ready", building)
        state = "disabled" if building else "normal"
        for button in (self.build_button, self.release_button):
            button.config(state=state)

    def handle_build_events(self):
        try:
            while True:
                kind, data = self.build_queue.get_nowait()
                if kind == "line":
                    self.build_log.append(data)
                    continue
                self.set_building(False)
                info = self.project_info
                if data == 0 and info and os.path.isfile(info.program_path):
                    self.write_output(f"Done: {os.path.relpath(info.program_path, info.folder)}\n"
                                      "You can give this program to anyone; it needs no Python.\n", "info")
                else:
                    self.write_output("The program could not be made. The last lines of the report:\n", "err")
                    self.write_output("\n".join(self.build_log[-20:]) + "\n", "err")
        except queue.Empty:
            pass

    def show_build_folder(self):
        if self.project_info is None:
            return
        info = self.project_info
        for folder in (info.dist_dir, info.build_dir, info.folder):
            if os.path.isdir(folder):
                open_folder(folder)
                return

    # ---- running -------------------------------------------------------------

    def child_command(self):
        return [sys.executable, "--run"] if FROZEN else [sys.executable, os.path.abspath(__file__), "--run"]

    def write_output(self, text, tag=None):
        self.output.config(state="normal")
        self.output.insert("end", text, tag)
        self.output.config(state="disabled")
        self.output.see("end")

    def clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")

    def run(self):
        tab = self.current()
        if tab is None:
            return
        self.runner.stop()
        self.run_id += 1
        run_id = self.run_id
        source = tab.source()
        self.run_tab = tab
        for t in self.tabs():
            t.clear_marks()
        self.clear_output()
        self.reset_watch()
        watch = self.watch_var.get() or self.live_var.get()
        for t in self.tabs():
            t.clear_inline()
        try:
            py_path = os.path.join(self.tmp, f"program{run_id}.py")
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(compile_to_python(source, watch=watch))
        except PlainError as err:
            self.show_compile_error(tab, source, err)
            return
        extra_env = None
        if watch:
            self.watch_file = os.path.join(self.tmp, f"watch{run_id}.json")
            extra_env = {"PLAIN_WATCH": self.watch_file}
        self.start_program(self.child_command() + [py_path], extra_env=extra_env)

    def show_compile_error(self, tab, source, err, run_id=None):
        if run_id is not None and run_id != self.run_id:
            return
        self.clear_output()
        self.set_running(False)
        self.write_output(format_error(err, source, tab.name) + "\n", "err")
        tab.mark_line(err.line)

    def start_program(self, cmd, run_id=None, extra_env=None):
        if run_id is not None and run_id != self.run_id:
            return
        self.clear_output()
        try:
            self.runner.start(cmd, extra_env)
        except OSError as exc:
            self.set_running(False)
            self.write_output(f"I could not start the program: {exc}\n", "err")
            return
        self.set_running(True)

    def stop(self):
        if self.runner.running:
            self.runner.stop()
            self.write_output("\n[stopped]\n", "info")

    def set_running(self, running):
        self.run_button.config(state="disabled" if running else "normal")
        self.stop_button.config(state="normal" if running else "disabled")
        self.entry.config(state="normal" if running else "disabled")
        self.set_status("Running..." if running else "Ready", running)
        if running:
            self.entry.focus_set()
        elif not running and self.current():
            self.current().text.focus_set()

    # ---- watching values -----------------------------------------------------

    def toggle_watch(self):
        shown = str(self.watch_frame) in self.editor_split.panes()
        if self.watch_var.get() and not shown:
            self.editor_split.add(self.watch_frame, weight=0)
        elif not self.watch_var.get() and shown:
            self.editor_split.forget(self.watch_frame)
        self.reset_watch()

    def reset_watch(self):
        self.watch_file = None
        self.watch_seq = 0
        self.watch_rows = {}
        self.watch_changed = {}
        self.watch_tree.delete(*self.watch_tree.get_children())
        self.watch_note.config(text="Run the program to see its values. Values that just changed "
                                    "are highlighted. Click a row to find it in the code.")

    def poll_watch(self):
        try:
            if (self.watch_var.get() or self.live_var.get()) and self.watch_file \
                    and os.path.exists(self.watch_file):
                with open(self.watch_file, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("seq") != self.watch_seq:
                    self.watch_seq = data["seq"]
                    if self.watch_var.get():
                        self.update_watch(data["vars"])
                    tab = self.run_tab
                    if self.live_var.get() and tab in self.tabs():
                        tab.set_inline({int(n): text for n, text in data.get("lines", {}).items()})
            now = time.time()
            for iid, since in list(self.watch_changed.items()):
                if now - since > 1.2:
                    if self.watch_tree.exists(iid):
                        self.watch_tree.item(iid, tags=())
                    del self.watch_changed[iid]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self.root.after(200, self.poll_watch)

    def update_watch(self, rows):
        for name, text, line in rows:
            iid = self.watch_rows.get(name)
            if iid is None:
                self.watch_rows[name] = self.watch_tree.insert("", "end", text=name, values=(text, line))
            elif self.watch_tree.set(iid, "value") != text:
                self.watch_tree.set(iid, "value", text)
                self.watch_tree.set(iid, "line", line)
                self.watch_tree.item(iid, tags=("changed",))
                self.watch_changed[iid] = time.time()

    def on_watch_select(self, _event):
        selected = self.watch_tree.selection()
        tab = self.run_tab if self.run_tab in self.tabs() else self.current()
        if not selected or tab is None:
            return
        name = self.watch_tree.item(selected[0], "text").split(": ")[-1]
        try:
            line = int(self.watch_tree.set(selected[0], "line"))
        except ValueError:
            return
        self.notebook.select(tab)
        tab.show_name(name, line)

    def send_input(self, _event):
        if not self.runner.running:
            return
        line = self.entry.get()
        self.entry.delete(0, "end")
        self.write_output(line + "\n", "in")
        self.runner.send(line)

    def poll(self):
        self.handle_build_events()
        try:
            while True:
                proc, kind, data = self.runner.events.get_nowait()
                if proc is not self.runner.proc:
                    continue
                if kind == "out":
                    for piece in data.splitlines(keepends=True):
                        failed = piece.startswith(("Error in line", "Error:"))
                        self.write_output(piece, "err" if failed else None)
                        m = re.match(r"Error in line (\d+):", piece)
                        if m and self.run_tab:
                            self.run_tab.mark_line(int(m.group(1)))
                else:
                    self.set_running(False)
                    if data not in (0, None):
                        self.write_output(f"\n[program ended with code {data}]\n", "info")
        except queue.Empty:
            pass
        self.root.after(40, self.poll)

    # ---- crash handling and recovery -----------------------------------------

    def install_crash_handler(self):
        self.root.report_callback_exception = lambda *info: self.report_crash("the window", *info)
        sys.excepthook = lambda *info: self.report_crash("the program", *info)
        if hasattr(threading, "excepthook"):
            threading.excepthook = lambda a: log_crash(f"thread {a.thread.name if a.thread else '?'}",
                                                       a.exc_type, a.exc_value, a.exc_traceback)

    def report_crash(self, where, exc_type, exc, tb):
        """Write the report, save every unsaved tab, and tell the user what happened."""
        if self.reporting:
            return
        self.reporting = True
        try:
            logged = log_crash(where, exc_type, exc, tb)
            saved = self.save_recovery()
            lines = ["Something went wrong inside the IDE."]
            lines.append("Your unsaved work was saved and will be offered again when you restart."
                         if saved else "I could not save a recovery copy of your work.")
            lines.append(f"Details: {LOG_PATH}" if logged else "I could not write the crash log.")
            lines.append(f"\n{exc_type.__name__}: {exc}")
            lines.append("\nKeep working? (No closes the IDE.)")
            try:
                keep = messagebox.askyesno(f"{TITLE} - problem", "\n".join(lines), icon="warning")
            except tk.TclError:
                keep = False
            if not keep:
                self.root.destroy()
        finally:
            self.reporting = False

    def save_recovery(self):
        """Store all unsaved tabs. Returns True if something was saved."""
        try:
            dirty = [t for t in self.tabs() if t.dirty]
            shutil.rmtree(RECOVERY_DIR, ignore_errors=True)
            if not dirty:
                return False
            os.makedirs(RECOVERY_DIR, exist_ok=True)
            index = []
            for n, tab in enumerate(dirty):
                name = f"tab{n}.plain"
                with open(os.path.join(RECOVERY_DIR, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write(tab.source())
                index.append({"file": name, "path": tab.path})
            with open(os.path.join(RECOVERY_DIR, "session.json"), "w", encoding="utf-8") as f:
                json.dump(index, f)
            return True
        except (OSError, tk.TclError):
            return False

    def autosave(self):
        self.save_recovery()
        self.root.after(20000, self.autosave)

    def restore_session(self):
        """Offer to bring back the unsaved work of a session that did not end normally."""
        index_path = os.path.join(RECOVERY_DIR, "session.json")
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
            items = []
            for entry in index:
                with open(os.path.join(RECOVERY_DIR, entry["file"]), encoding="utf-8") as f:
                    items.append((entry.get("path"), f.read()))
        except (OSError, ValueError, KeyError):
            return False
        if not items:
            return False
        if not messagebox.askyesno(TITLE, f"The IDE did not close normally last time.\n"
                                          f"Bring back {len(items)} unsaved tab(s)?"):
            shutil.rmtree(RECOVERY_DIR, ignore_errors=True)
            return False
        for path, content in items:
            tab = self.new_tab(path, content)
            tab.dirty = True
        return True

    def open_data_folder(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        open_folder(DATA_DIR)

    # ---- help ----------------------------------------------------------------

    def show_help(self):
        win = tk.Toplevel(self.root)
        win.title("Plain quick reference")
        win.configure(bg=self.theme["bg"])
        box = tk.Text(win, font=self.font, width=88, height=30, padx=14, pady=10, wrap="none", bd=0,
                      bg=self.theme["bg"], fg=self.theme["fg"], insertbackground=self.theme["fg"])
        box.insert("1.0", CHEAT_SHEET)
        box.config(state="disabled")
        box.pack(fill="both", expand=True)


def selftest(app, root, report):
    """Run the first tab with 'Live values' on and write what the IDE showed to a file, then quit."""
    root.withdraw()
    app.live_var.set(True)
    app.run()
    deadline = time.time() + 15

    def finish():
        tab = app.run_tab
        if app.runner.running and time.time() < deadline:
            root.after(200, finish)
            return
        root.after(600, lambda: write(tab))

    def write(tab):
        data = {"output": app.output.get("1.0", "end").strip(), "values": tab.inline if tab else {},
                "labels": len(tab.inline_labels) if tab else 0}
        with open(report, "w", encoding="utf-8") as f:
            json.dump(data, f)
        app.runner.stop()
        root.destroy()

    root.after(200, finish)


def main():
    try:
        root = tk.Tk()
        root.geometry("1240x800")
        root.minsize(680, 460)
        args = sys.argv[1:]
        report = None
        if args[:1] == ["--selftest"]:       # used by the build checks: run the file with live values, hidden
            report, args = args[1], args[2:]
            root.geometry("1100x760+4000+4000")
        app = App(root, args)
        if report:
            root.after(300, lambda: selftest(app, root, report))
        root.mainloop()
    except Exception:
        info = sys.exc_info()
        log_crash("startup", *info)
        try:
            messagebox.showerror(f"{TITLE} - problem", f"The IDE could not start.\n\n{info[1]}\n\nDetails: {LOG_PATH}")
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
