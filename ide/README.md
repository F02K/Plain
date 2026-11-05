# Plain IDE

A small editor for Plain, made for classrooms: one window, one Run button. It looks and works like
Visual Studio Code, with only the parts a beginner needs. It uses only Python's standard library (tkinter).

```
python ide/plain_ide.py                          # a new program
python ide/plain_ide.py game.plain a.plain       # open files
python ide/plain_ide.py MyGame.plainproject      # open a project
```

## The window

```
 menu
 toolbar          Run  Stop | Build  Release | Live values  Value list | Dark / Light
 +---+-------------+---------------------------------------------+
 | A | EXPLORER    | tabs:  main.plain  x   ball.plain  *  ...   |
 | c | MY GAME     |---------------------------------------------|
 | t |  v lessons  | editor                                      |
 | i |    hello    |                                             |
 | v |  main.plain |---------------------------------------------|
 | i |  MyGame.pl..| OUTPUT                                      |
 | t |             |  Input: ____________                        |
 | y |             |                                             |
 +---+-------------+---------------------------------------------+
 status bar:  Ready   Project: My Game          Ln 4, Col 1  Spaces: 4  Plain
```

- **Activity bar** (far left): *Explorer* and *Values*. Click the shown one again to hide the sidebar (Ctrl+B).
- **Tabs** have a close button (`x`) and a dot for unsaved changes; middle click closes, right click for more.
  Ctrl+Tab switches, Ctrl+W closes, Ctrl+N opens an empty tab.
- **Dark and light theme** (View menu, or the *Dark / Light* button). The choice is remembered.

## Projects and the Explorer

A project is a folder with a project file (`MyGame.plainproject`). *File > New project*, *Open project*
(the `.plainproject` file), *Open recent project* and *Open folder* work as you would expect. The first *Save*
of a new program asks for a folder and makes the project there.

The **Explorer** shows all files of the project, folders first. Without a project it offers *New project*,
*Open project*, *Open folder* and the recent projects.

| Do this | To get this |
| --- | --- |
| Click the **New file** / **New folder** icons, or right click > *New file...* | A name field appears right in the tree. Type `pong` and press Enter: `pong.plain` is made and opened. Esc cancels |
| Double click, or Enter | Open a file (folders open and close) |
| F2, or right click > *Rename* | Rename in place. Open tabs, and the main program, follow the new name |
| Delete, or right click > *Delete* | Delete (after asking). A tab that was open stays open as unsaved text, so nothing is lost |
| Right click a program > *Set as main program* | The program that *Build* and *Release* use. It is shown in bold with a green mark |
| Click the `.plainproject` file | Edit the project as text (`name`, `main`, `output`). Save, and the project changes at once. A mistake is explained in the output |
| Right click > *Project settings...* | The same in a small form |
| Right click > *Copy path*, *Show in file manager* | |
| **Refresh** / **Collapse all** icons | |

The tree keeps its open folders and notices files that were changed outside the IDE.
Folders `build`, `dist`, `__pycache__` and names that start with a dot are hidden.

**Go to file (Ctrl+P)** finds a file by a few letters of its name: type `bg` to find `ball_game.plain`.
Up and Down choose, Enter opens, Esc closes.

The project file is a few lines of text:

```
note: A Plain project. Open this file in the Plain IDE (File > Open project...).
name Ball Game
main ball.plain
output Ball_Game
```

## Writing programs

- **Auto completion** while you type (keywords, helpers and the names in your program).
  Up/Down choose, Tab or Enter accept, Esc closes, Ctrl+Space opens the list by hand.
  Accepting `if`, `while`, `repeat`, `for`, `action`, `define` or `try` fills in the whole block.
- Colors for words, strings, numbers and comments, line numbers, automatic indentation,
  `end` lines up with its block. Project files are colored too.
- **Click a name** (a variable, action, type or field) and the IDE marks where it is created (strong) and where it
  is used (light), and explains it in the line under the editor. Click a keyword to see what it does.
  Ctrl+click jumps to the place where the name is created.
- Other text files (`.txt`, ...) open as plain text, without Plain colors.
- Bigger / smaller text with Ctrl and + / -.

## Run, Build and Release

- **Run (F5)** is the debug mode: the program runs from the IDE, with output below the editor, and needs no
  project. Programs that use `input` get an input line. **Stop (Shift+F5)** ends a program that never finishes.
- **Live values** (toolbar) shows what happens while the program runs, right behind the code: the new value after
  `let` / `set`, the result of every condition (`-> true`), what `return` gives back, the values an action was
  called with and the numbers behind `draw` commands. The code itself is not changed; a value flashes when it
  changes. Editing the code removes the values.
- **Values** (activity bar, or *Value list* in the toolbar) lists all variables; click a row to find it in the code.
  Both are off by default, so they hardly slow the program down.
- **Build (F6)** translates the main program of the project to a Python file, `build/MyGame.py`. That file runs
  anywhere with Python 3.10+: `python build/MyGame.py`.
- **Release (F7)** builds first and then makes a program from the Python file, `dist/MyGame.exe`, that needs no Python.
  This needs Python and [PyInstaller](https://pyinstaller.org) on the computer that builds (the IDE offers to install
  PyInstaller with pip). Programs with a window get no console.
- Errors show the faulty line and mark it red in the editor.
- **Examples** menu with the programs from `examples/`, **Help > Quick reference** (F1) as a cheat sheet.

## Keys

| Key | |
| --- | --- |
| F5 / Shift+F5 | Run / Stop |
| F6 / F7 | Build / Release |
| Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S / Ctrl+W | New tab / Open / Save / Save as / Close tab |
| Ctrl+P | Go to file |
| Ctrl+B | Show or hide the sidebar |
| Ctrl+Shift+E | Go to the Explorer |
| F2 / Delete (in the Explorer) | Rename / Delete |
| Ctrl+Space | Auto completion |
| Ctrl + + / - | Bigger / smaller text |
| F1 | Quick reference |

## If something goes wrong

The IDE catches its own crashes: it writes a report to `crash.log`, saves every unsaved tab and
asks whether to keep working. Unsaved tabs are also saved every 20 seconds, so after a power cut or
a forced close the IDE offers to bring them back. Open the folder with *Help > Open crash log folder*
(Windows: `%LOCALAPPDATA%\PlainIDE`).

## Windows in programs

Programs can open windows with the `window` module (`import window`, then for example
`open window "Title" with width 640 and height 480`; see the Examples menu > ball). The program's
window opens next to the IDE; *Stop* or closing it ends the program.

## How the code is organized

`plain_ide.py` only starts the IDE. The program is the package `plainide/`, one file per job:

| File | Job |
| --- | --- |
| `app.py`, `main.py` | build the window and connect the parts; start-up |
| `explorer.py`, `activitybar.py` | the file tree (with new / rename / delete) and the view buttons |
| `documents.py`, `tabstrip.py`, `editor.py`, `completer.py` | open files, the row of tabs, one editor tab, the suggestion list |
| `output.py`, `values.py`, `statusbar.py`, `toolbar.py`, `menus.py`, `quickopen.py`, `dialogs.py` | the other parts of the window |
| `projects.py`, `projectui.py` | the `.plainproject` file and building; what the project menu does |
| `running.py`, `building.py`, `runner.py` | Run, Build / Release, the process that runs a program |
| `session.py`, `crash.py` | crash handling and recovery of unsaved work |
| `theme.py`, `icons.py`, `language.py`, `helptext.py`, `symbols.py` | colors, pictures drawn in code, what the editor knows about Plain |
| `paths.py`, `settings.py` | where files live; remembered settings |

Tests: `python tests/ide_tests.py` (needs tkinter and a display; `xvfb-run -a python tests/ide_tests.py` on a
Linux machine without one). The logic of `symbols.py` and `projects.py` is also checked by `tests/run_tests.py`.

## Build a program that needs no Python

```
pip install pyinstaller
python ide/build.py
```

The result is `ide/dist/PlainIDE` (`PlainIDE.exe` on Windows).
