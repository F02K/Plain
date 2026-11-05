"""Modules: parts of Plain that live outside the language itself.

A module is a folder in modules/ with a Plain file and a Python file:

    modules/window/window.plain       types, fixed values and the actions the module offers
    modules/window/window_impl.py     the Python code that does the work

`import window` reads window.plain like any imported file of your own (see docs/language.md), with two extra
lines that only module files may use: `export` gives a type to Python and `from python` lists what Python
provides. See docs/modules.md.
"""

import ast
import os
import re
import sys


def modules_dir():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (getattr(sys, "_MEIPASS", None), here):
        if base and os.path.isdir(os.path.join(base, "modules")):
            return os.path.join(base, "modules")
    return os.path.join(here, "modules")


def available():
    folder = modules_dir()
    if not os.path.isdir(folder):
        return []
    return sorted(n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n, n + ".plain")))


def module_path(name):
    """The .plain file of the module with this name, or None when there is no such module."""
    if name not in available():
        return None
    return os.path.join(modules_dir(), name, name + ".plain")


NAME_LINE = re.compile(r"^\s*(?:define\s+(\w+)|(?:action|question)\s+(\w+)|let\s+(\w+)\s+be\s+Color\()", re.M)


def provided_names():
    """name -> module name, for the types, actions, questions and colors that the modules offer.
    Used to say 'import window' when someone uses one of them without the import."""
    names = {}
    for module in available():
        with open(module_path(module), encoding="utf-8") as f:
            for match in NAME_LINE.finditer(f.read()):
                names.setdefault(next(g for g in match.groups() if g), module)
    return names


def color_names():
    """The names of the colors that the modules make (for the editor)."""
    names = []
    for module in available():
        with open(module_path(module), encoding="utf-8") as f:
            names += re.findall(r"^let\s+(\w+)\s+be\s+Color\(", f.read(), re.M)
    return names


def python_api(path):
    """What a Python file offers at its top: name -> ("class", 0, 0) or ("function", fewest, most values).
    None when the file cannot be read."""
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        return None
    api = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            api[node.name] = ("class", 0, 0)
        elif isinstance(node, ast.FunctionDef):
            args = node.args
            most = 10 ** 6 if args.vararg else len(args.args)
            api[node.name] = ("function", len(args.args) - len(args.defaults), most)
    return api


def python_source(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
