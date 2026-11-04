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
from plain.library import CALLS, OF  # noqa: E402
from plain.toolchain import ToolError, build_executable, compile_source, compile_to_python, host_target  # noqa: E402

TITLE = "Plain IDE"
VERSION = "0.2"
NEW_PROGRAM = 'say "Hello, world!"\n'
INDENT = "    "
OPENERS = re.compile(r"\b(then|do|as|times)$")
TOKEN = re.compile(r'(?P<comment>\bnote:[^\n]*)|(?P<string>"(?:[^"\\\n]|\\.)*"?)|'
                   r'(?P<number>\b\d+(?:\.\d+)?\b)|(?P<word>[A-Za-z_][A-Za-z0-9_]*)')
WORD_BEFORE_CURSOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
HELPERS = set(CALLS) | set(OF)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Words that expand into a whole block when you accept them in the completion list.
# {i} is the indentation of the current line, | marks where the cursor ends up.
SNIPPETS = {
    "if": "if | then\n{i}    \n{i}end",
    "while": "while | do\n{i}    \n{i}end",
    "repeat": "repeat | times\n{i}    \n{i}end",
    "for": "for each | in  do\n{i}    \n{i}end",
    "action": "action |name() do\n{i}    \n{i}end",
    "define": "define |Name as\n{i}    field as number\n{i}end",
    "try": "try\n{i}    |\n{i}catch error then\n{i}    \n{i}end",
}

LIGHT = {
    "bg": "#ffffff", "fg": "#1f2328", "gutter_bg": "#f3f4f6", "gutter_fg": "#8a8f98",
    "keyword": "#0b5cad", "helper": "#7a3db8", "string": "#1a7f37", "number": "#b35900",
    "comment": "#8a8f98", "error_line": "#ffd9d9",
    "out_bg": "#fafafa", "out_err": "#c62828", "out_in": "#0b5cad", "out_info": "#6b7280",
    "pop_bg": "#ffffff", "pop_sel": "#cfe3ff",
}

CHEAT_SHEET = """\
Variables        let health be 100          set health to health - 5
Output / input   say "Hello"                let name be input "Name?"
                 let age be input number "Age?"
Decisions        if x > 3 then ... else if ... then ... else ... end
Loops            repeat 3 times ... end     while x > 0 do ... end
                 for each item in items do ... end      stop / skip
Actions          action add(a, b) do  return a + b  end
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
Windows          window("Title", 640, 480)   color(r, g, b)   clear()   show()
                 rectangle(x, y, w, h)      circle(x, y, r)  line(x1, y1, x2, y2)
                 write("text", x, y)         running()        close_window()
                 pressed("left")  mouse_x()  mouse_y()  mouse_down()
Errors           try ... catch error then ... end
Comments         note: this is a comment

In the editor    F5 run, Shift+F5 stop, Ctrl+Space complete, Tab/Enter accept a suggestion
                 Ctrl+N new tab, Ctrl+W close tab, Ctrl+Tab next tab, Ctrl+O open, Ctrl+S save
                 'if', 'while', 'repeat', 'for', 'action', 'define' and 'try' fill in a whole block
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

class Runner:
    """Starts a program in its own process and streams its output."""

    def __init__(self):
        self.proc = None
        self.events = queue.Queue()

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd):
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
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
        words = set(KEYWORDS) | HELPERS
        for m in TOKEN.finditer(self.tab.text.get("1.0", "end-1c")):
            if m.lastgroup == "word":
                words.add(m.group())
        low = prefix.lower()
        found = [w for w in words if w.lower().startswith(low) and w != prefix]
        found.sort(key=lambda w: (w not in KEYWORDS and w not in HELPERS, w.lower()))
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
        suffix = "(" if word in CALLS else " of " if word in OF else ""
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
        self.line_count = 0
        self.untitled = None
        if path is None:
            app.untitled_count += 1
            self.untitled = f"Untitled {app.untitled_count}"
        t = app.theme
        font = app.font

        self.gutter = tk.Text(self, width=4, padx=6, pady=4, font=font, bg=t["gutter_bg"], fg=t["gutter_fg"],
                              bd=0, highlightthickness=0, state="disabled", cursor="arrow", takefocus=0,
                              wrap="none")
        self.gutter.tag_configure("right", justify="right")
        self.text = tk.Text(self, font=font, bg=t["bg"], fg=t["fg"], insertbackground=t["fg"], undo=True,
                            wrap="none", bd=0, highlightthickness=0, padx=8, pady=4, tabs=(font.measure(INDENT),))
        self.yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.config(yscrollcommand=self.on_yscroll, xscrollcommand=xscroll.set)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.yscroll.grid(row=0, column=2, sticky="ns")
        xscroll.grid(row=1, column=1, sticky="ew")

        for tag in ("keyword", "helper", "string", "number", "comment"):
            self.text.tag_configure(tag, foreground=t[tag])
        self.text.tag_configure("error_line", background=t["error_line"])
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
        self.text.bind("<ButtonRelease-1>", lambda e: (self.completer.hide(), self.clear_marks()))
        # The text widget has its own Ctrl keys (Ctrl+O opens a new line...), so route ours through it.
        for key, action in (("n", app.new_tab), ("o", app.open_dialog), ("s", app.save), ("S", app.save_as),
                            ("w", app.close_tab), ("Tab", app.next_tab), ("Shift-Tab", lambda: app.next_tab(-1))):
            self.text.bind(f"<Control-{key}>", lambda e, action=action: (action(), "break")[1])
        self.gutter.bind("<MouseWheel>", self.on_wheel)
        self.gutter.bind("<Button-4>", self.on_wheel)
        self.gutter.bind("<Button-5>", self.on_wheel)

        self.set_text(content)

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
        if self.highlight_job:
            self.after_cancel(self.highlight_job)
        self.highlight_job = self.after(120, self.rehighlight)

    # ---- look ----------------------------------------------------------------

    def on_yscroll(self, first, last):
        self.yscroll.set(first, last)
        self.gutter.yview_moveto(first)

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
        for m in TOKEN.finditer(self.source()):
            kind = m.lastgroup
            if kind == "word":
                word = m.group()
                kind = "keyword" if word in KEYWORDS else "helper" if word in HELPERS else None
                if kind is None:
                    continue
            self.text.tag_add(kind, f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    def clear_marks(self):
        self.text.tag_remove("error_line", "1.0", "end")

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
        self.theme = LIGHT
        self.runner = Runner()
        self.tmp = tempfile.mkdtemp(prefix="plain_ide_")
        self.untitled_count = 0
        self.run_id = 0
        self.run_tab = None
        self.project = None
        self.ui_queue = queue.Queue()
        self.reporting = False
        self.folder_nodes = {}

        base = tkfont.nametofont("TkFixedFont").copy()
        family = "Consolas" if sys.platform.startswith("win") else base.actual("family")
        self.font = tkfont.Font(family=family, size=13)

        self.build_menu()
        self.build_toolbar()
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
        root.after(20000, self.autosave)

    # ---- layout --------------------------------------------------------------

    def build_menu(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New tab", accelerator="Ctrl+N", command=self.new_tab)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_dialog)
        file_menu.add_command(label="Open folder (project)...", command=self.open_project_dialog)
        file_menu.add_command(label="Close folder", command=self.close_project)
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

        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Bigger text", accelerator="Ctrl++", command=lambda: self.zoom(1))
        view_menu.add_command(label="Smaller text", accelerator="Ctrl+-", command=lambda: self.zoom(-1))
        menu.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Quick reference", accelerator="F1", command=self.show_help)
        help_menu.add_command(label="Open crash log folder", command=lambda: self.open_data_folder())
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(6, 4))
        bar.pack(side="top", fill="x")
        self.run_button = ttk.Button(bar, text="▶  Run (F5)", command=self.run)
        self.run_button.pack(side="left")
        self.stop_button = ttk.Button(bar, text="■  Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))
        ttk.Label(bar, text="Run with:").pack(side="left", padx=(18, 4))
        self.backend = tk.StringVar(value="Python")
        ttk.Combobox(bar, textvariable=self.backend, values=["Python", "Assembly"], width=8,
                     state="readonly").pack(side="left")

    def build_panes(self):
        t = self.theme
        self.hpane = ttk.PanedWindow(self.root, orient="horizontal")
        self.hpane.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(self.hpane)
        self.project_label = ttk.Label(self.sidebar, text="", padding=(6, 4), font=("TkDefaultFont", 9, "bold"))
        self.project_label.grid(row=0, column=0, sticky="ew")
        ttk.Button(self.sidebar, text="+ New file", command=self.new_project_file).grid(
            row=0, column=1, sticky="e", padx=4)
        self.tree = ttk.Treeview(self.sidebar, show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=tree_scroll.set)
        self.tree.grid(row=1, column=0, columnspan=2, sticky="nsew")
        tree_scroll.grid(row=1, column=2, sticky="ns")
        self.sidebar.rowconfigure(1, weight=1)
        self.sidebar.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self.on_tree_open)
        self.tree.bind("<Return>", self.on_tree_open)

        main = ttk.Frame(self.hpane)
        self.hpane.add(main, weight=1)
        vpane = ttk.PanedWindow(main, orient="vertical")
        vpane.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(vpane)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.on_tab_switch())
        self.notebook.bind("<ButtonRelease-2>", self.on_tab_middle_click)
        self.notebook.bind("<Button-3>", self.on_tab_right_click)
        vpane.add(self.notebook, weight=3)

        bottom = ttk.Frame(vpane)
        self.output = tk.Text(bottom, font=self.font, bg=t["out_bg"], fg=t["fg"], height=9, wrap="word", bd=0,
                              highlightthickness=0, padx=8, pady=4, state="disabled")
        out_scroll = ttk.Scrollbar(bottom, orient="vertical", command=self.output.yview)
        self.output.config(yscrollcommand=out_scroll.set)
        self.output.tag_configure("err", foreground=t["out_err"])
        self.output.tag_configure("in", foreground=t["out_in"])
        self.output.tag_configure("info", foreground=t["out_info"])
        entry_row = ttk.Frame(bottom, padding=(6, 4))
        ttk.Label(entry_row, text="Input:").pack(side="left")
        self.entry = ttk.Entry(entry_row, state="disabled")
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.entry.bind("<Return>", self.send_input)
        bottom.rowconfigure(0, weight=1)
        bottom.columnconfigure(0, weight=1)
        self.output.grid(row=0, column=0, sticky="nsew")
        out_scroll.grid(row=0, column=1, sticky="ns")
        entry_row.grid(row=1, column=0, columnspan=2, sticky="ew")
        vpane.add(bottom, weight=1)

        self.tab_menu = tk.Menu(self.root, tearoff=False)
        self.tab_menu.add_command(label="Close tab", command=lambda: self.close_tab(self.menu_tab))
        self.tab_menu.add_command(label="Close other tabs", command=self.close_other_tabs)
        self.menu_tab = None

    def bind_keys(self):
        r = self.root
        r.bind("<F5>", lambda e: self.run())
        r.bind("<Shift-F5>", lambda e: self.stop())
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

    def on_tab_switch(self):
        for t in self.tabs():
            t.completer.hide()
        self.tab_changed()

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
        self.project_label.config(text=os.path.basename(self.project) or self.project)
        if str(self.sidebar) not in self.hpane.panes():
            self.hpane.insert(0, self.sidebar, weight=0)
            self.root.after(50, lambda: self.hpane.sashpos(0, 210))
        self.refresh_tree()

    def close_project(self):
        self.project = None
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

    def on_tree_open(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        path, kind = self.tree.item(selection[0], "values")
        if kind == "file":
            self.open_path(path)

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
        if self.backend.get() == "Assembly":
            if not (shutil.which("nasm") and shutil.which("gcc")):
                self.write_output("The Assembly backend needs NASM and gcc, and I cannot find them.\n"
                                  "Install them (see the README) or choose 'Python' next to the Run button.\n", "err")
                return
            self.write_output("Compiling...\n", "info")
            self.set_running(True, compiling=True)
            threading.Thread(target=self.compile_assembly, args=(run_id, tab, source), daemon=True).start()
            return
        try:
            py_path = os.path.join(self.tmp, f"program{run_id}.py")
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(compile_to_python(source))
        except PlainError as err:
            self.show_compile_error(tab, source, err)
            return
        self.start_program(self.child_command() + [py_path])

    def compile_assembly(self, run_id, tab, source):
        """Runs in a thread so the window stays alive while NASM and gcc work."""
        exe = os.path.join(self.tmp, f"program{run_id}" + (".exe" if host_target() == "windows" else ""))
        try:
            build_executable(compile_source(source, host_target()), exe, host_target())
            result = lambda: self.start_program([exe], run_id)  # noqa: E731
        except PlainError as err:
            result = lambda err=err: self.show_compile_error(tab, source, err, run_id)  # noqa: E731
        except ToolError as err:
            result = lambda err=err: self.show_tool_error(err, run_id)  # noqa: E731
        except Exception:  # keep the thread's crash visible instead of a silent "Compiling..."
            info = sys.exc_info()
            log_crash("assembly compile", *info)
            message = f"The compiler failed: {info[1]}"
            result = lambda: self.show_tool_error(message, run_id)  # noqa: E731
        self.ui_queue.put(result)

    def show_compile_error(self, tab, source, err, run_id=None):
        if run_id is not None and run_id != self.run_id:
            return
        self.clear_output()
        self.set_running(False)
        self.write_output(format_error(err, source, tab.name) + "\n", "err")
        tab.mark_line(err.line)

    def show_tool_error(self, err, run_id):
        if run_id != self.run_id:
            return
        self.set_running(False)
        self.clear_output()
        self.write_output(str(err) + "\n", "err")

    def start_program(self, cmd, run_id=None):
        if run_id is not None and run_id != self.run_id:
            return
        self.clear_output()
        try:
            self.runner.start(cmd)
        except OSError as exc:
            self.set_running(False)
            self.write_output(f"I could not start the program: {exc}\n", "err")
            return
        self.set_running(True)

    def stop(self):
        if self.runner.running:
            self.runner.stop()
            self.write_output("\n[stopped]\n", "info")
        elif self.stop_button.cget("state") == "normal":    # still compiling
            self.run_id += 1
            self.set_running(False)
            self.write_output("\n[stopped]\n", "info")

    def set_running(self, running, compiling=False):
        self.run_button.config(state="disabled" if running else "normal")
        self.stop_button.config(state="normal" if running else "disabled")
        self.entry.config(state="normal" if running and not compiling else "disabled")
        if running and not compiling:
            self.entry.focus_set()
        elif not running and self.current():
            self.current().text.focus_set()

    def send_input(self, _event):
        if not self.runner.running:
            return
        line = self.entry.get()
        self.entry.delete(0, "end")
        self.write_output(line + "\n", "in")
        self.runner.send(line)

    def poll(self):
        try:
            while True:
                self.ui_queue.get_nowait()()
        except queue.Empty:
            pass
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
        box = tk.Text(win, font=self.font, width=88, height=30, padx=10, pady=8, wrap="none", bd=0)
        box.insert("1.0", CHEAT_SHEET)
        box.config(state="disabled")
        box.pack(fill="both", expand=True)


def main():
    try:
        root = tk.Tk()
        root.geometry("1100x760")
        root.minsize(560, 420)
        App(root, sys.argv[1:])
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
