"""Calls the assembler (nasm) and the linker (gcc) to produce an executable."""

import os
import shutil
import subprocess
import sys
import tempfile

from .codegen import compile_program
from .pygen import generate_python
from .errors import PlainError
from .lexer import tokenize
from .parser import parse


def _add_known_tool_folders():
    """On Windows, find NASM and MinGW-w64 in their usual folders even if PATH is out of date."""
    if not sys.platform.startswith("win"):
        return
    local = os.environ.get("LOCALAPPDATA", "")
    folders = [r"C:\Program Files\NASM", r"C:\Program Files (x86)\NASM",
               os.path.join(local, "bin", "NASM"), os.path.join(local, "Programs", "NASM"),
               os.path.join(local, "Microsoft", "WinGet", "Links"),
               r"C:\msys64\ucrt64\bin", r"C:\msys64\mingw64\bin", r"C:\mingw64\bin",
               r"C:\ProgramData\chocolatey\bin"]
    packages = os.path.join(local, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(packages):
        for name in os.listdir(packages):
            if name.startswith(("BrechtSanders.WinLibs", "NASM.NASM")):
                root = os.path.join(packages, name)
                folders += [root, os.path.join(root, "mingw64", "bin"), os.path.join(root, "mingw32", "bin")]
    have = os.environ.get("PATH", "").lower().split(os.pathsep)
    extra = [f for f in folders if os.path.isdir(f) and f.lower() not in have]
    if extra:
        os.environ["PATH"] = os.pathsep.join(extra + [os.environ.get("PATH", "")])


_add_known_tool_folders()


def host_target():
    return "windows" if sys.platform.startswith("win") else "linux"


def compile_source(source, target):
    """Plain source text -> NASM assembly text."""
    return compile_program(parse(tokenize(source)), target)


def compile_to_python(source):
    """Plain source text -> Python source text.

    The program is type checked first by the normal compiler, so both backends
    accept and reject exactly the same programs.
    """
    program = parse(tokenize(source))
    compile_program(program, "python")
    return generate_python(program)


class ToolError(Exception):
    pass


def _run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise ToolError(f"I could not find the program '{cmd[0]}'. Please install it and try again.")
    if result.returncode != 0:
        raise ToolError(f"'{' '.join(cmd)}' failed:\n{result.stderr or result.stdout}")


def build_executable(asm_text, output, target, keep_asm=None):
    """Assemble and link. Returns the path of the executable (or object file)."""
    with tempfile.TemporaryDirectory() as tmp:
        asm_path = os.path.join(tmp, "program.asm")
        with open(asm_path, "w", encoding="utf-8") as f:
            f.write(asm_text)
        if keep_asm:
            shutil.copyfile(asm_path, keep_asm)
        obj_path = os.path.join(tmp, "program.obj" if target == "windows" else "program.o")
        _run(["nasm", "-f", "win64" if target == "windows" else "elf64", asm_path, "-o", obj_path])

        if target == "linux":
            _run(["gcc", "-no-pie", obj_path, "-o", output, "-lm"])
            return output

        linker = None
        if host_target() == "windows":
            linker = shutil.which("gcc")
        else:
            linker = shutil.which("x86_64-w64-mingw32-gcc")
        if linker is None:
            object_output = os.path.splitext(output)[0] + ".obj"
            shutil.copyfile(obj_path, object_output)
            raise ToolError(
                f"No Windows linker found (need MinGW-w64 gcc). I saved the object file: {object_output}\n"
                "Link it on Windows with:  gcc program.obj -o program.exe")
        _run([linker, obj_path, "-o", output, "-luser32", "-lgdi32"])
        return output
