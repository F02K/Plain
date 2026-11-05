"""The types of Plain.

Primitive types are plain strings. Compound types are tuples:
    ('list', element_type)
    ('struct', name)
"""

NUMBER = "number"
TEXT = "text"
BOOLEAN = "boolean"
NOTHING = "nothing"
ANY = "any"         # only used while checking an action that is never called: its values are not known


PRIMITIVES = (NUMBER, TEXT, BOOLEAN)


def list_of(element):
    return ("list", element)


def struct(name):
    return ("struct", name)


def is_list(t):
    return isinstance(t, tuple) and t[0] == "list"


def is_struct(t):
    return isinstance(t, tuple) and t[0] == "struct"


def type_name(t):
    """Human readable name used in error messages."""
    if is_list(t):
        return f"list of {type_name(t[1])}"
    if is_struct(t):
        return t[1]
    return t
