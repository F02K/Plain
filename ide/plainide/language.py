"""What the editor knows about Plain: words to color, blocks to fill in, how to indent."""

import re

from plain import modules as MODULES
from plain.library import CALLS, OF
from plain.lexer import KEYWORDS

NEW_PROGRAM = 'say "Hello, world!"\n'
INDENT = "    "
OPENERS = re.compile(r"\b(then|do|as|times)$")
WORD_BEFORE_CURSOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
HELPER_CALLS = set(CALLS)
HELPERS = HELPER_CALLS | set(OF)
OF_HELPERS = set(OF)

# The sentences of the modules are highlighted as a whole, so that names like 'size' stay ordinary names.
PHRASES = re.compile(MODULES.highlight_regex() + r'|\btakes(?=\s*\()|\bkey(?= (?:"[^"\n]*"|\w+) is pressed)')
COLOR_WORD = re.compile(r"(?<=color )(?:" + "|".join(MODULES.color_names()) + r")\b")

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

# The words of a project file (see projects.py): 'name Space Game', 'main main.plain', 'output Space_Game'
PROJECT_KEYS = re.compile(r"^(name|main|output)\b", re.M)


def kind_of(path):
    """How to treat a file in the editor: 'plain' (a program), 'project' (a .plainproject) or 'text'."""
    from .projects import EXT
    if path is None or path.endswith(".plain"):
        return "plain"
    if path.endswith(EXT):
        return "project"
    return "text"
