"""Test runner.

Run programs:   tests/cases/NAME.plain  ->  compare the output with NAME.out
                (on both backends: assembly and Python)
                (optional NAME.in is sent to the program as keyboard input)
Windows:        tests/windows/NAME.plain -> like tests/cases, but with hidden windows
                (PLAIN_HEADLESS=1). Only on Windows: the assembly backend opens windows with Win32 there.
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


def run_case(path, tmp, env=None):
    name = os.path.splitext(os.path.basename(path))[0]
    source = read(path)
    exe = os.path.join(tmp, name + (".exe" if sys.platform.startswith("win") else ""))
    try:
        build_executable(compile_source(source, host_target()), exe, host_target())
    except PlainError as err:
        return False, format_error(err, source, os.path.basename(path))
    stdin_path = path[:-6] + ".in"
    stdin = read(stdin_path) if os.path.exists(stdin_path) else ""
    result = subprocess.run([exe], input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=20, env=env)
    expected = read(path[:-6] + ".out")
    if result.stdout != expected:
        return False, f"[assembly] expected:\n{expected}\ngot:\n{result.stdout}{result.stderr}"
    py_path = os.path.join(tmp, name + ".py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write(compile_to_python(source))
    result = subprocess.run([sys.executable, py_path], input=stdin, capture_output=True, text=True, encoding="utf-8",
                            timeout=20, env=env)
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


def symbol_checks():
    """The IDE explains a name when you click it (ide/symbols.py). Checked here without opening any window."""
    sys.path.insert(0, os.path.join(ROOT, "ide"))
    from symbols import analyze
    source = read(os.path.join(ROOT, "examples", "ball.plain"))
    lines = source.splitlines()

    def at(word, after):
        for number, text in enumerate(lines, 1):
            col = text.find(word)
            if number >= after and col >= 0:
                return number, col + 1
        raise AssertionError(word)

    expected = [("speed_x", 5, "field", 4), ("paddle", 5, "variable", 6), ("move_paddle", 5, "action", 2),
                ("position", 5, "parameter", 1), ("while", 5, "help", 0)]
    for word, after, kind, uses in expected:
        found = analyze(source, *at(word, after))
        if found["kind"] != kind or len(found["uses"]) != uses:
            return False, f"{word}: expected {kind} with {uses} uses, got {found['kind']} with {len(found['uses'])}"
    return True, ""


def main():
    failures = 0
    total = 1
    ok, detail = symbol_checks()
    print(("PASS " if ok else "FAIL ") + "ide/symbols.py")
    if not ok:
        failures += 1
        print(detail)
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(glob.glob(os.path.join(ROOT, "tests", "cases", "*.plain"))):
            total += 1
            ok, detail = run_case(path, tmp)
            print(("PASS " if ok else "FAIL ") + os.path.relpath(path, ROOT))
            if not ok:
                failures += 1
                print(detail)
    if sys.platform.startswith("win"):
        hidden = dict(os.environ, PLAIN_HEADLESS="1")
        with tempfile.TemporaryDirectory() as tmp:
            for path in sorted(glob.glob(os.path.join(ROOT, "tests", "windows", "*.plain"))):
                total += 1
                ok, detail = run_case(path, tmp, hidden)
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
