# Plain IDE

A small editor for Plain, made for classrooms: one window, one Run button.

- **Tabs** for several files (Ctrl+N new, Ctrl+W close, Ctrl+Tab next, middle click closes)
- **Projects:** a project is a folder with a project file (`MyGame.plainproject`). The first *Save* of a new
  program asks for a folder and makes the project there. *File > New project*, *Open project* (the
  `.plainproject` file) and *Open recent project* work as you would expect; **+ New file** adds a program to the project
- **Auto completion** while you type (keywords, helpers and the names in your program).
  Up/Down choose, Tab or Enter accept, Esc closes, Ctrl+Space opens the list by hand.
  Accepting `if`, `while`, `repeat`, `for`, `action`, `define` or `try` fills in the whole block
- Colours for words, strings, numbers and comments, line numbers, automatic indentation,
  `end` lines up with its block
- **Run (F5)** shows the output below the editor; programs that use `input` get an input line
- **Stop (Shift+F5)** ends a program that never finishes
- **Click a name** (a variable, action, type or field) and the IDE marks where it is created (strong) and where it
  is used (light), and explains it in the line under the editor. Click a keyword to see what it does.
  Ctrl+click jumps to the place where the name is created
- **Live values** (next to the Run button) shows what happens while the program runs, right behind the code:
  the new value after `let` / `set`, the result of every condition (`-> true`), what `return` gives back,
  the values an action was called with (`hits_paddle(Ball(...), 200) -> false` and, at the action's first line,
  `takes ball = ..., position = 200`) and the numbers behind `draw` commands. The code itself is not changed;
  a value flashes when it changes. Editing the code removes the values.
- **Value list** opens a list of all variables on the right; click a row to find it in the code.
  Both report a few times per second and are off by default,
  so they hardly slow the program down
- Errors show the faulty line and mark it red in the editor
- **Examples** menu with the programs from `examples/`, **Help > Quick reference** (F1) as a cheat sheet
- Bigger / smaller text with Ctrl and + / -

## Run, Build and Release

- **Run (F5)** is the debug mode: the program runs from the IDE, with live values, and needs no project.
- **Build (F6)** translates the main program of the project to a Python file, `build/MyGame.py`. That file runs
  anywhere with Python 3.10+: `python build/MyGame.py`.
- **Release (F7)** builds first and then makes a program from the Python file, `dist/MyGame.exe`, that needs no Python.
  This needs Python and [PyInstaller](https://pyinstaller.org) on the computer that builds (the IDE offers to install
  PyInstaller with pip). Programs with a window get no console.
- *Build > Project settings* changes the name, the main program and the file name of the program.
  *Build > Show build folder* opens `dist` (or `build`).

The project file is a few lines of text; it can be edited by hand:

```
note: A Plain project. Open this file in the Plain IDE (File > Open project...).
name Ball Game
main ball.plain
output Ball_Game
```

## If something goes wrong

The IDE catches its own crashes: it writes a report to `crash.log`, saves every unsaved tab and
asks whether to keep working. Unsaved tabs are also saved every 20 seconds, so after a power cut or
a forced close the IDE offers to bring them back. Open the folder with *Help > Open crash log folder*
(Windows: `%LOCALAPPDATA%\PlainIDE`).

## Windows

Programs can open windows with the `window` module (`import window`, then for example
`open window "Title" with width 640 and height 480`; see the Examples menu > ball). The program's
window opens next to the IDE; *Stop* or closing it ends the program.

## Start

```
python ide/plain_ide.py                      # new program
python ide/plain_ide.py game.plain a.plain   # open files
```

## Build a program that needs no Python

```
pip install pyinstaller
python ide/build.py
```

The result is `ide/dist/PlainIDE` (`PlainIDE.exe` on Windows). The IDE uses only Python's
standard library (tkinter); `plain_ide.py` is the whole source.
