"""Modules: parts of Plain that live outside the language itself.

A module is a folder in modules/ with two files:

    modules/window/window.plain   says which sentences the module adds (the compiler reads this)
    modules/window/window.py      the Python code that runs when one of the sentences is used

A program asks for a module with `import window`. Only then do its sentences exist. See docs/modules.md.
"""

import os
import re
import sys

from . import nodes as N
from . import typesys as T

VALUE_TYPES = {"text": T.TEXT, "number": T.NUMBER, "boolean": T.BOOLEAN}
EXAMPLE_DEFAULTS = {"text": '"text"', "number": "1", "boolean": "true", "color": "orange"}
PLACEHOLDER = re.compile(r"<(\w+):\s*(\w+)(?:\s*=\s*(.*?))?>$", re.S)
PART = re.compile(r"<[^>]*>|,|[A-Za-z_]+")


def modules_dir():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (getattr(sys, "_MEIPASS", None), here):
        if base and os.path.isdir(os.path.join(base, "modules")):
            return os.path.join(base, "modules")
    return os.path.join(here, "modules")


class Part:
    """One piece of a sentence: a word, a comma, or a value that is filled in."""

    def __init__(self, kind, word=None, name=None, type=None, example=None):
        self.kind = kind            # "word", "comma" or "value"
        self.word = word
        self.name = name
        self.type = type            # text, number, boolean or color
        self.example = example


class Pattern:
    def __init__(self, module, kind, parts, gives, func):
        self.module = module        # module name
        self.kind = kind            # "command" (a line of its own) or "question" (gives a value)
        self.parts = parts
        self.gives = gives
        self.func = func            # the Python function that does the work
        self.head = 0               # how many words the sentence starts with, before the first value
        for part in parts:
            if part.kind != "word":
                break
            self.head += 1

    def head_words(self):
        return [p.word for p in self.parts[:self.head]]

    def arg_types(self):
        """The types of the values the Python function receives (a color arrives as three numbers)."""
        types = []
        for part in self.parts:
            if part.kind == "value":
                types += [T.NUMBER] * 3 if part.type == "color" else [VALUE_TYPES[part.type]]
        return types

    def result_type(self):
        return T.NOTHING if self.gives is None else VALUE_TYPES[self.gives]

    def example(self):
        """The sentence with the example values filled in, for hints."""
        words = []
        for part in self.parts:
            if part.kind == "word":
                words.append(part.word)
            elif part.kind == "comma":
                words[-1] += ","
            else:
                words.append(part.example or EXAMPLE_DEFAULTS[part.type])
        return " ".join(words)

    def snippet(self):
        """The sentence for auto completion; | marks where the cursor goes."""
        text, marked = self.example(), False
        for part in self.parts:
            if part.kind == "value":
                example = part.example or EXAMPLE_DEFAULTS[part.type]
                text = text.replace(example, "|" + example, 1)
                marked = True
                break
        return text if marked else text + "|"

    def phrases(self):
        """Runs of fixed words, for highlighting: 'draw circle at', 'radius', ..."""
        runs, current = [], []
        for part in self.parts:
            if part.kind == "word":
                current.append(part.word)
            else:
                if current:
                    runs.append(" ".join(current))
                current = []
        if current:
            runs.append(" ".join(current))
        return runs


class Module:
    def __init__(self, name, folder):
        self.name = name
        self.folder = folder
        self.python = None
        self.structs = []           # (name, [(field, type), ...])
        self.colors = {}            # name -> (red, green, blue)
        self.patterns = []

    def python_source(self):
        with open(os.path.join(self.folder, self.python), encoding="utf-8") as f:
            return f.read()

    def struct_nodes(self):
        return [N.DefineStruct(name, [(f, t, 0) for f, t in fields], line=0, col=0) for name, fields in self.structs]

    def commands(self):
        return [p for p in self.patterns if p.kind == "command"]

    def questions(self):
        return [p for p in self.patterns if p.kind == "question"]


def _parse_pattern(module, kind, text, lineno):
    gives = None
    text, func = text.rsplit(" = ", 1)
    m = re.search(r"\s+gives\s+(\w+)\s*$", text)
    if m:
        gives = m.group(1)
        text = text[:m.start()]
    parts = []
    for piece in PART.findall(text):
        if piece == ",":
            parts.append(Part("comma"))
        elif piece.startswith("<"):
            pm = PLACEHOLDER.match(piece)
            if not pm or (pm.group(2) not in VALUE_TYPES and pm.group(2) != "color"):
                raise ValueError(f"{module.name}.plain line {lineno}: I do not understand '{piece}'")
            parts.append(Part("value", name=pm.group(1), type=pm.group(2), example=pm.group(3)))
        else:
            parts.append(Part("word", word=piece))
    if gives is not None and gives not in VALUE_TYPES:
        raise ValueError(f"{module.name}.plain line {lineno}: unknown type '{gives}'")
    return Pattern(module.name, kind, parts, gives, func.strip())


def _parse_module(name, folder, path):
    module = Module(name, folder)
    block = None            # None, ("type", name, fields) or ("colors",)
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for lineno, raw in enumerate(lines, 1):
        text = raw.strip()
        if not text or text.startswith("note:"):
            continue
        if block:
            if text == "end":
                if block[0] == "type":
                    module.structs.append((block[1], block[2]))
                block = None
            elif block[0] == "type":
                field, _as, ftype = text.split()
                block[2].append((field, ftype))
            else:
                color, r, g, b = text.split()
                module.colors[color] = (int(r), int(g), int(b))
            continue
        word = text.split()[0]
        if word == "module":
            if text.split()[1] != name:
                raise ValueError(f"{path} line {lineno}: the module is called '{text.split()[1]}', not '{name}'")
        elif word == "python":
            module.python = text.split()[1]
        elif word == "type":
            block = ("type", text.split()[1], [])
        elif word == "colors":
            block = ("colors",)
        elif word in ("command", "question"):
            module.patterns.append(_parse_pattern(module, word, text[len(word):].strip(), lineno))
        else:
            raise ValueError(f"{path} line {lineno}: I do not understand '{text}'")
    if module.python is None:
        raise ValueError(f"{path}: the module needs a line like 'python {name}.py'")
    return module


_cache = {}


def available():
    folder = modules_dir()
    if not os.path.isdir(folder):
        return []
    return sorted(n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n, n + ".plain")))


def load(name):
    """The module with this name, or None when there is none."""
    if name not in _cache:
        path = os.path.join(modules_dir(), name, name + ".plain")
        _cache[name] = _parse_module(name, os.path.dirname(path), path) if name in available() else None
    return _cache[name]


def load_all():
    return [load(name) for name in available()]


def pattern_for(module_name, func):
    for pattern in load(module_name).patterns:
        if pattern.func == func:
            return pattern
    return None


def highlight_regex():
    """A regular expression for the fixed words of the module sentences (for the IDE).
    Only runs of two or more words count, so a single word like 'size' stays an ordinary name."""
    phrases = set()
    for module in load_all():
        for pattern in module.patterns:
            phrases.update(p for p in pattern.phrases() if " " in p)
    ordered = sorted(phrases, key=lambda p: (-len(p), p))
    return r"\b(?:" + "|".join(re.escape(p) for p in ordered) + r")\b" if ordered else r"(?!x)x"


def color_names():
    names = []
    for module in load_all():
        names += list(module.colors)
    return names
