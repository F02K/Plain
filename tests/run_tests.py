"""Test runner.

Run programs:   tests/cases/NAME.plain  ->  compare the output with NAME.out
                (on both backends: native assembly and Python)
                (optional NAME.in is sent to the program as keyboard input)
Compile errors: tests/errors/NAME.plain ->  the error message must contain
                every line of NAME.err

Usage: python3 tests/run_tests.py
"""

import glob
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from plain.errors import PlainError, format_error  # noqa: E402
from plain.toolchain import build_executable, compile_source, compile_to_python, host_target  # noqa: E402


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_case(path, tmp):
    name = os.path.splitext(os.path.basename(path))[0]
    source = read(path)
    exe = os.path.join(tmp, name)
    try:
        build_executable(compile_source(source, host_target()), exe, host_target())
    except PlainError as err:
        return False, format_error(err, source, os.path.basename(path))
    stdin_path = path[:-6] + ".in"
    stdin = read(stdin_path) if os.path.exists(stdin_path) else ""
    result = subprocess.run([exe], input=stdin, capture_output=True, text=True, timeout=20)
    expected = read(path[:-6] + ".out")
    if result.stdout != expected:
        return False, f"[native] expected:\n{expected}\ngot:\n{result.stdout}{result.stderr}"
    py_path = os.path.join(tmp, name + ".py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write(compile_to_python(source))
    result = subprocess.run([sys.executable, py_path], input=stdin, capture_output=True, text=True, timeout=20)
    if result.stdout != expected:
        return False, f"[python] expected:\n{expected}\ngot:\n{result.stdout}{result.stderr}"
    return True, ""


def error_case(path):
    source = read(path)
    try:
        compile_source(source, host_target())
    except PlainError as err:
        text = format_error(err, source, os.path.basename(path))
        missing = [line for line in read(path[:-6] + ".err").splitlines() if line and line not in text]
        return not missing, f"missing {missing} in:\n{text}"
    return False, "the program compiled but an error was expected"


def main():
    failures = 0
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(glob.glob(os.path.join(ROOT, "tests", "cases", "*.plain"))):
            total += 1
            ok, detail = run_case(path, tmp)
            print(("PASS " if ok else "FAIL ") + os.path.relpath(path, ROOT))
            if not ok:
                failures += 1
                print(detail)
    for path in sorted(glob.glob(os.path.join(ROOT, "tests", "errors", "*.plain"))):
        total += 1
        ok, detail = error_case(path)
        print(("PASS " if ok else "FAIL ") + os.path.relpath(path, ROOT))
        if not ok:
            failures += 1
            print(detail)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
