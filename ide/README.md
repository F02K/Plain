# Plain IDE

A small editor for Plain, made for classrooms: one window, one Run button.

- **Tabs** for several files (Ctrl+N new, Ctrl+W close, Ctrl+Tab next, middle click closes)
- **Projects:** *File > Open folder...* shows the programs of a folder on the left; double-click opens one,
  **+ New file** adds one to the project
- **Auto completion** while you type (keywords, helpers and the names in your program).
  Up/Down choose, Tab or Enter accept, Esc closes, Ctrl+Space opens the list by hand.
  Accepting `if`, `while`, `repeat`, `for`, `action`, `define` or `try` fills in the whole block
- Colours for words, strings, numbers and comments, line numbers, automatic indentation,
  `end` lines up with its block
- **Run (F5)** shows the output below the editor; programs that use `input` get an input line
- **Stop (Shift+F5)** ends a program that never finishes
- Errors show the faulty line and mark it red in the editor
- **Examples** menu with the programs from `examples/`, **Help > Quick reference** (F1) as a cheat sheet
- Bigger / smaller text with Ctrl and + / -

## If something goes wrong

The IDE catches its own crashes: it writes a report to `crash.log`, saves every unsaved tab and
asks whether to keep working. Unsaved tabs are also saved every 20 seconds, so after a power cut or
a forced close the IDE offers to bring them back. Open the folder with *Help > Open crash log folder*
(Windows: `%LOCALAPPDATA%\PlainIDE`).

## Windows

Programs can open windows (`window("Title", 640, 480)`, see the Examples menu > ball). The program's
window opens next to the IDE; *Stop* or closing it ends the program.

## Run with Python or Assembly

Programs run with the Python backend by default, so a school computer only needs Python
(or the packaged program below). *Run with: Assembly* builds a real program and needs NASM and gcc
(see the main README); the IDE finds them in their usual folders even when `PATH` is out of date.

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
