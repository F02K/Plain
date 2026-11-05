"""Command line interface: plain run|python <file.plain>"""

import argparse
import os
import subprocess
import sys
import tempfile

from .errors import PlainError, format_error
from .toolchain import compile_to_python

VERSION = "0.2.0"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="plain", description="The Plain programming language.")
    parser.add_argument("--version", action="version", version=f"plain {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a program")
    run.add_argument("file")

    py = sub.add_parser("python", help="translate a program to a Python file")
    py.add_argument("file")
    py.add_argument("-o", "--output", help="name of the .py file")

    args = parser.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as f:
            source = f.read()
    except OSError as exc:
        print(f"I cannot read '{args.file}': {exc.strerror}", file=sys.stderr)
        return 2

    try:
        py_text = compile_to_python(source, base_dir=os.path.dirname(os.path.abspath(args.file)))
    except PlainError as err:
        print(format_error(err, source, os.path.basename(args.file)), file=sys.stderr)
        return 1

    if args.command == "python":
        out = args.output or os.path.splitext(args.file)[0] + ".py"
        with open(out, "w", encoding="utf-8") as f:
            f.write(py_text)
        print(f"Wrote {out}")
        return 0

    if getattr(sys, "frozen", False):
        # The packaged program has no separate Python, so run the translation here.
        try:
            exec(compile(py_text, "<plain>", "exec"), {"__name__": "__main__"})
        except SystemExit as stop:
            return stop.code or 0
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "program.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(py_text)
        return subprocess.run([sys.executable, path]).returncode


if __name__ == "__main__":
    sys.exit(main())
