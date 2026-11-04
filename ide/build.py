"""Build the Plain IDE as one program that needs no Python.

    pip install pyinstaller
    python ide/build.py [output folder]

The result is ide/dist/PlainIDE (PlainIDE.exe on Windows).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "dist")
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "PlainIDE",
        "--paths", ROOT,
        "--add-data", os.path.join(ROOT, "examples") + os.pathsep + "examples",
        "--distpath", out,
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
        os.path.join(HERE, "plain_ide.py"),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
