"""Build the stand-alone `plain` program (needs no Python).

    pip install pyinstaller
    python packaging/build_cli.py [output folder]

The result is packaging/dist/plain (plain.exe on Windows). The modules folder is packed into it.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "dist")
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "plain",
        "--paths", ROOT,
        "--add-data", os.path.join(ROOT, "modules") + os.pathsep + "modules",
        "--distpath", out,
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
        os.path.join(HERE, "plain_cli.py"),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
