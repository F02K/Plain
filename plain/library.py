"""Names and types of the built-in helpers, used by the checker and the Python writer.

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
    "index_of": ((T.TEXT, T.TEXT), T.NUMBER),
    "starts_with": ((T.TEXT, T.TEXT), T.BOOLEAN),
    "ends_with": ((T.TEXT, T.TEXT), T.BOOLEAN),
    "replace": ((T.TEXT, T.TEXT, T.TEXT), T.TEXT),
    "split": ((T.TEXT, T.TEXT), T.list_of(T.TEXT)),
    "join": ((T.list_of(T.TEXT), T.TEXT), T.TEXT),
    "read_file": ((T.TEXT,), T.TEXT),
    "write_file": ((T.TEXT, T.TEXT), T.NOTHING),        # run write_file("a.txt", "hello")
    "append_file": ((T.TEXT, T.TEXT), T.NOTHING),
    "file_exists": ((T.TEXT,), T.BOOLEAN),
}

# name -> (argument type, result type)
OF = {
    "length": (T.TEXT, T.NUMBER),
    "upper": (T.TEXT, T.TEXT),
    "lower": (T.TEXT, T.TEXT),
    "round": (T.NUMBER, T.NUMBER),
    "abs": (T.NUMBER, T.NUMBER),
    "sqrt": (T.NUMBER, T.NUMBER),
    "trim": (T.TEXT, T.TEXT),
    "number": (T.TEXT, T.NUMBER),                       # number of "42" is 42
    "text": ([T.NUMBER, T.BOOLEAN, T.TEXT], T.TEXT),    # text of 42 is "42"
}

EXAMPLES = {
    "random": "random(1, 6)",
    "min": "min(3, 8)",
    "max": "max(3, 8)",
    "part": 'part("Hello", 0, 2)',
    "contains": 'contains("Hello", "ell") or contains(scores, 10)',
    "index_of": 'index_of("Hello", "ll")',
    "starts_with": 'starts_with("Hello", "He")',
    "ends_with": 'ends_with("Hello", "lo")',
    "replace": 'replace("Hello", "l", "L")',
    "split": 'split("a,b,c", ",")',
    "join": 'join(words, ", ")',
    "read_file": 'read_file("notes.txt")',
    "write_file": 'run write_file("notes.txt", "Hello")',
    "append_file": 'run append_file("notes.txt", "one more line")',
    "file_exists": 'file_exists("notes.txt")',
}

# Calls that can fail at run time get the line number as an extra last argument.
NEEDS_LINE = ("random", "part", "replace", "number")
