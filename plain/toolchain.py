"""Plain source text -> Python source text."""

from .checker import check_program
from .lexer import tokenize
from .parser import parse
from .pygen import generate_python


def compile_to_python(source, watch=False):
    """Check a Plain program and translate it to Python.

    The checker runs first, so a program with a mistake in it never reaches Python.
    watch=True adds hooks that let the IDE show the values while the program runs.
    """
    program = parse(tokenize(source))
    check_program(program)
    return generate_python(program, watch)
