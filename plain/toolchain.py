"""Plain source text -> Python source text."""

from .checker import check_program
from .lexer import tokenize
from .parser import parse
from .pygen import generate_python


def compile_to_python(source, watch=False, base_dir=None):
    """Check a Plain program and translate it to Python.

    The checker runs first, so a program with a mistake in it never reaches Python.
    watch=True adds hooks that let the IDE show the values while the program runs.
    base_dir is the folder of the program: 'import name' finds the file name.plain there.
    """
    program = parse(tokenize(source), base_dir)
    check_program(program)
    return generate_python(program, watch)
