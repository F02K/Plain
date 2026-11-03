"""Command line interface: plain run|build|asm|python <file.plain>"""

import argparse
import os
import subprocess
import sys
import tempfile

from .errors import PlainError, format_error
from .toolchain import ToolError, build_executable, compile_source, compile_to_python, host_target

VERSION = "0.1.0"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="plain", description="The Plain programming language.")
    parser.add_argument("--version", action="version", version=f"plain {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="compile a program and run it")
    run.add_argument("file")
    run.add_argument("--backend", choices=["native", "python"], default="native",
                     help="native: assembly (default); python: translate to Python and run it")

    build = sub.add_parser("build", help="compile a program to an executable")
    build.add_argument("file")
    build.add_argument("-o", "--output", help="name of the executable")
    build.add_argument("--target", choices=["linux", "windows"], default=host_target())

    asm = sub.add_parser("asm", help="only write the assembly file (NASM syntax)")
    asm.add_argument("file")
    asm.add_argument("-o", "--output", help="name of the .asm file")
    asm.add_argument("--target", choices=["linux", "windows"], default=host_target())

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

    target = getattr(args, "target", host_target())
    base = os.path.splitext(args.file)[0]
    try:
        if args.command == "python" or (args.command == "run" and args.backend == "python"):
            py_text = compile_to_python(source)
        else:
            asm_text = compile_source(source, target)
    except PlainError as err:
        print(format_error(err, source, os.path.basename(args.file)), file=sys.stderr)
        return 1

    try:
        if args.command == "python":
            out = args.output or base + ".py"
            with open(out, "w", encoding="utf-8") as f:
                f.write(py_text)
            print(f"Wrote {out}")
            return 0
        if args.command == "run" and args.backend == "python":
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "program.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(py_text)
                return subprocess.run([sys.executable, path]).returncode
        if args.command == "asm":
            out = args.output or base + ".asm"
            with open(out, "w", encoding="utf-8") as f:
                f.write(asm_text)
            print(f"Wrote {out}")
            return 0
        if args.command == "build":
            ext = ".exe" if target == "windows" else ""
            out = args.output or base + ext
            build_executable(asm_text, out, target)
            print(f"Built {out}")
            return 0
        # run
        if host_target() == "windows":
            suffix = ".exe"
        else:
            suffix = ""
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "program" + suffix)
            build_executable(asm_text, exe, host_target())
            return subprocess.run([exe]).returncode
    except ToolError as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
