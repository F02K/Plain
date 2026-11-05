"""Test runner.

Run programs:   tests/cases/NAME.plain  ->  compare the output with NAME.out
                (optional NAME.in is sent to the program as keyboard input)
Windows:        tests/windows/NAME.plain -> like tests/cases, but the windows stay hidden (PLAIN_HEADLESS=1)
Compile errors: tests/errors/NAME.plain ->  the error message must contain
                every line of NAME.err

Usage: python3 tests/run_tests.py
"""

import glob
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from plain.errors import PlainError, format_error  # noqa: E402
from plain.toolchain import compile_to_python  # noqa: E402


NL = chr(10)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_case(path, tmp, env=None):
    name = os.path.splitext(os.path.basename(path))[0]
    source = read(path)
    try:
        python_text = compile_to_python(source, base_dir=os.path.dirname(path))
    except PlainError as err:
        return False, format_error(err, source, os.path.basename(path))
    py_path = os.path.join(tmp, name + ".py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write(python_text)
    stdin_path = path[:-6] + ".in"
    stdin = read(stdin_path) if os.path.exists(stdin_path) else ""
    work = os.path.join(tmp, name + "_work")            # the program runs here, so files it writes stay here
    os.makedirs(work, exist_ok=True)
    result = subprocess.run([sys.executable, py_path], input=stdin, capture_output=True, text=True,
                            encoding="utf-8", timeout=20, env=env, cwd=work)
    expected = read(path[:-6] + ".out")
    if result.stdout != expected:
        return False, f"expected:{NL}{expected}{NL}got:{NL}{result.stdout}{result.stderr}"
    return True, ""


def error_case(path):
    source = read(path)
    try:
        compile_to_python(source, base_dir=os.path.dirname(path))
    except PlainError as err:
        text = format_error(err, source, os.path.basename(path))
        missing = [line for line in read(path[:-6] + ".err").splitlines() if line and line not in text]
        return not missing, f"missing {missing} in:{NL}{text}"
    return False, "the program compiled but an error was expected"


def symbol_checks():
    """The IDE explains a name when you click it (ide/plainide/symbols.py). Checked here without opening any window."""
    sys.path.insert(0, os.path.join(ROOT, "ide"))
    from plainide.symbols import analyze
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


def project_checks():
    """Projects of the IDE (ide/plainide/projects.py): definition file, recent list and the Python build."""
    sys.path.insert(0, os.path.join(ROOT, "ide"))
    from plainide import projects as P
    with tempfile.TemporaryDirectory() as tmp:
        folder = os.path.join(tmp, "My Game")
        os.makedirs(folder)
        with open(os.path.join(folder, "main.plain"), "w", encoding="utf-8") as f:
            f.write("say 6 * 7" + chr(10))
        project = P.Project(folder, "My Game", "main.plain")
        project.save()
        loaded = P.Project.load(project.path)
        if (loaded.name, loaded.main, loaded.output) != ("My Game", "main.plain", "My_Game"):
            return False, f"the project file was read back as {(loaded.name, loaded.main, loaded.output)}"
        if P.Project.find(folder) is None:
            return False, "the project file was not found in its folder"
        python_file, imports = P.build_python(loaded)
        result = subprocess.run([sys.executable, python_file], capture_output=True, text=True)
        if result.stdout.strip() != "42":
            return False, f"the built Python file printed {result.stdout!r}"
        data = os.path.join(tmp, "data")
        P.add_recent(data, project.path)
        P.add_recent(data, project.path)
        if len(P.recent_projects(data)) != 1:
            return False, "the recent list holds a project twice"
        os.remove(project.path)
        if P.recent_projects(data):
            return False, "the recent list still shows a project whose file is gone"
    return True, ""


def packaging_checks():
    """One version number (plain/__init__.py) for the language, the command and the IDE; the IDE is in the package."""
    import plain
    from plain import cli
    sys.path.insert(0, os.path.join(ROOT, "ide"))
    import plainide
    text = read(os.path.join(ROOT, "pyproject.toml"))
    if 'dynamic = ["version"]' not in text or re.search(r'^version\s*=\s*"', text, re.M):
        return False, "pyproject.toml must take the version from plain.__version__"
    if '"plainide"' not in text or "plain-ide" not in text:
        return False, "pyproject.toml must include the IDE package and the plain-ide command"
    if not (plain.__version__ == cli.VERSION == plainide.VERSION):
        return False, f"versions differ: {plain.__version__}, {cli.VERSION}, {plainide.VERSION}"
    return True, ""


def main():
    failures = 0
    total = 3
    for label, check in (("ide/plainide/symbols.py", symbol_checks), ("ide/plainide/projects.py", project_checks),
                         ("pyproject.toml (version, IDE package)", packaging_checks)):
        ok, detail = check()
        print(("PASS " if ok else "FAIL ") + label)
        if not ok:
            failures += 1
            print(detail)
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(glob.glob(os.path.join(ROOT, "tests", "cases", "*.plain"))):
            if not os.path.exists(path[:-6] + ".out"):
                continue            # a library that the test programs import (see tests/cases/lib_*.plain)
            total += 1
            ok, detail = run_case(path, tmp)
            print(("PASS " if ok else "FAIL ") + os.path.relpath(path, ROOT))
            if not ok:
                failures += 1
                print(detail)
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
        if not os.path.exists(path[:-6] + ".err"):
            continue                # a file that the test programs import
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
