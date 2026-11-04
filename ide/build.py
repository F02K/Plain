"""Build the Plain IDE as one program that needs no Python.

    pip install pyinstaller
    python ide/build.py

The result is ide/dist/PlainIDE (PlainIDE.exe on Windows).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "PlainIDE",
        "--paths", ROOT,
        "--add-data", os.path.join(ROOT, "examples") + os.pathsep + "examples",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
        os.path.join(HERE, "plain_ide.py"),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
