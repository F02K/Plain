"""Plain projects: a folder with a project definition file, a Python build and a program build.

    MyGame/
        MyGame.plainproject    the project definition (open this file in the IDE)
        main.plain             your programs
        build/MyGame.py        "Build": the program translated to Python (runs with plain Python)
        dist/MyGame.exe        "Release": the Python file made into a program that needs no Python

Running a program from the IDE (F5) is the debug mode and does not need a project.
"""

import json
import os
import re
import shutil
import subprocess
import sys

EXT = ".plainproject"
HEADER = "note: A Plain project. Open this file in the Plain IDE (File > Open project...)."
MAX_RECENT = 10
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def slug(name):
    """A name that is safe as a file name: 'Ball Game!' -> 'Ball_Game'."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return cleaned or "program"


class Project:
    def __init__(self, folder, name=None, main="main.plain", output=None):
        self.folder = os.path.abspath(folder)
        self.name = name or os.path.basename(self.folder) or "program"
        self.main = main
        self.output = output or slug(self.name)
        self.file = None            # the project file it was read from (it may have another name than the slug)

    # ---- files ---------------------------------------------------------------

    @property
    def path(self):
        return self.file or os.path.join(self.folder, slug(self.name) + EXT)

    @property
    def main_path(self):
        return os.path.join(self.folder, self.main)

    @property
    def build_dir(self):
        return os.path.join(self.folder, "build")

    @property
    def dist_dir(self):
        return os.path.join(self.folder, "dist")

    @property
    def python_path(self):
        return os.path.join(self.build_dir, self.output + ".py")

    @property
    def program_path(self):
        return os.path.join(self.dist_dir, self.output + (".exe" if sys.platform.startswith("win") else ""))

    # ---- the definition file -------------------------------------------------

    def save(self):
        os.makedirs(self.folder, exist_ok=True)
        text = f"{HEADER}\nname {self.name}\nmain {self.main}\noutput {self.output}\n"
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return self.path

    @staticmethod
    def load(path):
        """Read a project definition file. Raises ValueError with a friendly message."""
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            raise ValueError(f"I cannot read this project file: {exc.strerror}")
        return Project.from_text(text, path)

    @staticmethod
    def from_text(text, path):
        """Read the text of a project file (also text that is being edited and not saved yet)."""
        values = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("note:"):
                continue
            key, _, value = line.partition(" ")
            if key not in ("name", "main", "output"):
                raise ValueError(f"I do not understand the line '{line}' in the project file. "
                                 "A project file has the lines: name, main and output.")
            values[key] = value.strip()
        folder = os.path.dirname(os.path.abspath(path))
        project = Project(folder, values.get("name"), values.get("main") or "main.plain", values.get("output"))
        project.file = os.path.abspath(path)
        return project

    @staticmethod
    def find(folder):
        """The project definition file in a folder, as a Project (or None)."""
        try:
            for name in sorted(os.listdir(folder)):
                if name.endswith(EXT):
                    return Project.load(os.path.join(folder, name))
        except (OSError, ValueError):
            pass
        return None

    def plain_files(self):
        found = []
        for dirpath, dirs, files in os.walk(self.folder):
            dirs[:] = [d for d in dirs if d not in ("build", "dist", "__pycache__") and not d.startswith(".")]
            for f in sorted(files):
                if f.endswith(".plain"):
                    found.append(os.path.relpath(os.path.join(dirpath, f), self.folder).replace("\\", "/"))
        return found


# ---- recent projects -----------------------------------------------------------------

def _recent_file(data_dir):
    return os.path.join(data_dir, "recent_projects.json")


def recent_projects(data_dir):
    """Paths of the project files opened lately, newest first. Files that are gone are left out."""
    try:
        with open(_recent_file(data_dir), encoding="utf-8") as f:
            paths = json.load(f)
    except (OSError, ValueError):
        return []
    return [p for p in paths if isinstance(p, str) and os.path.isfile(p)][:MAX_RECENT]


def add_recent(data_dir, path):
    path = os.path.abspath(path)
    paths = [p for p in recent_projects(data_dir) if os.path.normcase(p) != os.path.normcase(path)]
    paths.insert(0, path)
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(_recent_file(data_dir), "w", encoding="utf-8") as f:
            json.dump(paths[:MAX_RECENT], f)
    except OSError:
        pass


def clear_recent(data_dir):
    try:
        os.remove(_recent_file(data_dir))
    except OSError:
        pass


# ---- building ------------------------------------------------------------------------------

def build_python(project):
    """Translate the main program of the project to Python. Returns (path of the .py file, modules used).

    Raises PlainError when the program has a mistake, OSError when a file cannot be read or written.
    """
    from plain.lexer import tokenize
    from plain.parser import parse
    from plain.checker import check_program
    from plain.pygen import generate_python

    with open(project.main_path, encoding="utf-8") as f:
        source = f.read()
    program = parse(tokenize(source), os.path.dirname(project.main_path))
    check_program(program)
    text = generate_python(program)
    os.makedirs(project.build_dir, exist_ok=True)
    with open(project.python_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return project.python_path, list(program.imports)


def python_commands():
    """Commands that start a Python on this computer (not the IDE itself when it is a packaged program)."""
    commands = []
    if not getattr(sys, "frozen", False):
        commands.append([sys.executable])
    for name in ("python", "python3"):
        path = shutil.which(name)
        if path:
            commands.append([path])
    if shutil.which("py"):
        commands.append([shutil.which("py"), "-3"])
    return commands


def _works(command, *args):
    try:
        result = subprocess.run(command + list(args), capture_output=True, timeout=60, creationflags=NO_WINDOW)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def find_python(need_pyinstaller=True):
    """A Python command (list) that can run PyInstaller, or the first working Python, or None."""
    working = [c for c in python_commands() if _works(c, "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)")]
    if not working:
        return None, False
    for command in working:
        if _works(command, "-m", "PyInstaller", "--version"):
            return command, True
    return working[0], False


def pyinstaller_arguments(project, windowed):
    args = ["-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--name", project.output,
            "--distpath", project.dist_dir,
            "--workpath", os.path.join(project.build_dir, "pyinstaller"),
            "--specpath", os.path.join(project.build_dir, "pyinstaller")]
    if windowed:
        args.append("--windowed")      # a program with a window gets no console next to it
    args.append(project.python_path)
    return args
