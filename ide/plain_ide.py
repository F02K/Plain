"""Plain IDE: a small editor for Plain programs, made for classrooms.

    python ide/plain_ide.py [file.plain | project.plainproject ...]

The program itself lives in the package ide/plainide/ (see its __init__.py for a map of the files).
This file only starts it. It is also the program that runs a translated Plain program in a separate
process (the Run button), so the Stop button always works and the packaged IDE needs no Python:

    plain_ide.py --run program.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)
if not FROZEN:
    sys.path.insert(0, os.path.dirname(HERE))      # the plain compiler
    sys.path.insert(0, HERE)                       # the plainide package

if len(sys.argv) >= 3 and sys.argv[1] == "--run":
    with open(sys.argv[2], encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, sys.argv[2], "exec"), {"__name__": "__main__"})
    sys.exit(0)

from plainide.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
