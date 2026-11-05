"""python -m plainide: start the IDE, or (with --run) run a translated Plain program in this process."""

import sys

if len(sys.argv) >= 3 and sys.argv[1] == "--run":
    with open(sys.argv[2], encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, sys.argv[2], "exec"), {"__name__": "__main__"})
    sys.exit(0)

from .main import main  # noqa: E402

sys.exit(main())
