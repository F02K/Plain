# Modules

Not everything belongs in the language itself. Windows and drawing, for example, are a **module**.
A program asks for a module in the first lines:

```
import window

let win be Window(title: "Plain Ball", width: 480, height: 320)
while open of win do
    run clear of win
    run draw_circle(240, 160, 30, orange) of win
    run show of win
end
```

A module is written in Plain, like your own files (see [Modules and your own files](language.md#modules-and-your-own-files)).
`import window` brings in its types (`Window`, `Color`), its fixed values (the color names) and its actions
(`clear`, `draw_circle`, ...). Without the import they do not exist. If you use one anyway, Plain tells you where
it comes from:

```
'Window' belongs to the module 'window', which is not imported.
Hint: Add this line at the very top of your program:  import window
```

`import` lines go at the top, before everything else (comments are fine).

## Things, fields and actions

A module follows the same rules as the rest of Plain:

| You want to | You write | Like |
| --- | --- | --- |
| make a thing | `let win be Window(title: "Game", width: 640, height: 480)` | `Player(x: 0, health: 100)` |
| read a value | `open of win`, `mouse_x of win` | `health of hero` |
| change a value | `set color of win to orange` | `set health of hero to 90` |
| do something | `run clear of win`, `run draw_circle(40, 40, 8) of win` | `run heal(hero, 20)` |
| ask something | `is_down("left") of win` | `area(shape)` |

Anything that only *is* something (is the window open? where is the mouse?) is a field. Anything that *does*
something is an action with `run`.

### The action form `name(values) of thing`

The thing an action works on is written after `of` and is the action's first value:

```
run draw_circle(40, 40, 8, red) of win      note: the same as  run draw_circle(win, 40, 40, 8, red)
run show of win                             note: no values besides the thing: no brackets
if is_down("left") of win then ...          note: also inside conditions
```

Values can be given with their names, in any order (plain values first):

```
run draw_circle(40, 40, radius: 8, color: red) of win
run draw_circle(radius: 8, y: 40, x: 40) of win
```

This works for every action, also your own (`run heal(amount: 20) of hero`, `heal(hero, amount: 20)`).

## The window module

Everything is a field or an action of a `Window`. `(0, 0)` is the top left corner, `x` grows to the right and `y`
grows downwards.

| | What it does |
| --- | --- |
| `Window(title: "t", width: 640, height: 480)` | opens a window (only one at a time). `background` and `color` are optional. |
| `open of win` | `true` while the window is open (`false` after the player closed it or after `close`) |
| `title of win`, `width of win`, `height of win` | what the window was made with (the size cannot change) |
| `mouse_x of win`, `mouse_y of win` | where the mouse is inside the window |
| `mouse_down of win` | `true` while the left mouse button is held down |
| `background of win` | the color that `clear` fills the window with (change it with `set`, default `black`) |
| `color of win` | the color that is drawn next when no color is given (default `white`) |
| `run clear of win` | fills the whole window with its background color |
| `run show of win` | shows what was drawn and waits for the next frame (about 60 per second) |
| `run close of win` | closes the window from the program |
| `run draw_rectangle(x, y, width, height, color) of win` | a filled rectangle with its top left corner at `x, y` |
| `run draw_circle(x, y, radius, color) of win` | a filled circle around `x, y` |
| `run draw_line(x1, y1, x2, y2, color) of win` | a line |
| `run draw_text("Score", x, y, color) of win` | text with its top left corner at `x, y` |
| `is_down("left") of win` | `true` while the key is held down. Keys: `"left"`, `"right"`, `"up"`, `"down"`, `"space"`, `"enter"`, `"escape"`, `"shift"`, `"ctrl"`, `"tab"`, `"backspace"`, `"a"` to `"z"`, `"0"` to `"9"`. The key can also be a text variable. |

The `color` of every drawing action is optional. Without it the action uses `color of win`:

```
set color of win to orange
run draw_circle(40, 40, 8) of win           note: orange
run draw_circle(80, 40, 8, red) of win      note: red, only for this circle
```

### Colors

- The color names are fixed values of the type `Color`: `red`, `green`, `blue`, `yellow`, `orange`, `purple`,
  `pink`, `brown`, `gray`, `white`, `black`.
- Your own colors are things of the type `Color` with the fields `red`, `green` and `blue` (0 to 255):

  ```
  let sky be Color(red: 20, green: 24, blue: 40)
  set background of win to sky
  set red of sky to 100
  ```
- Because the names are fixed values, a variable of your own cannot be called `red`, `green`, `orange`, ... (Plain tells you).

### Things to know

- Drawing happens in the background; nothing appears until `run show of win`. Use `run clear of win` at the start of each
  picture, otherwise old drawings stay.
- Events (closing the window, keys) are handled inside `show`, so call it in every round of your loop.
- When the program ends while the window is open, the window stays until it is closed.
- Drawing after the window was closed does nothing.
- The window uses tkinter, which comes with Python. Set the environment variable `PLAIN_HEADLESS=1` to keep
  windows hidden (used by the tests).
- See [`examples/ball.plain`](../examples/ball.plain), [`paint.plain`](../examples/paint.plain) and
  [`shapes.plain`](../examples/shapes.plain).

## Writing a module

A module is a folder in `modules/` with a Plain file and a Python file:

```
modules/window/window.plain       what the module offers
modules/window/window_impl.py     the Python code that does the work
```

`window.plain` is ordinary Plain (`define`, `let ... fixed`, `action`) plus two lines that only module files may use.
They say in which direction things go:

```
define Window as
    title as text
    width as number
    height as number
    background as Color = black             note: a field can have a value for when none is given
    color as Color = white
    open as boolean readonly                note: only Python changes it: Plain code can read it, not set it
    mouse_x as number readonly
end

export Window as window to python "window_impl"      note: Plain gives Python this type

from python "window_impl"                            note: Python gives Plain these actions
    action clear of window
    action draw_circle(x as number, y as number, radius as number, color as Color = color of window) of window
    question is_down(key as text) of window gives boolean
end
```

- **`export Window as window to python "file"`**: the type `Window` is built by the class `Window` in the Python file.
  `window` is the short name of the thing inside this module file: the lines below use it after `of`.
- **`from python "file" ... end`** lists the actions (`action`) and questions (`question`, they need `gives <type>`)
  that the Python file provides. `of window` says which thing the action works on. In brackets come the other
  values, with their types. `= color of window` is a default: the value that is used when the caller leaves it out
  (it may use the thing: `window` is replaced by the caller's thing).
- Plain checks the Python file when the module is loaded: the class and every function must exist and take the right
  number of values.

The Python file:

```python
class Window:
    def __init__(self, title, width, height, background, color):
        # called by Window(title: ..., width: ..., ...): the fields that are not readonly, in the order of `define`
        self.title = title
        self.open = True

    @property
    def mouse_x(self):                  # open of win, mouse_x of win ... read the attribute of the same name
        return 0.0


def clear(window, line):                # run clear of win
    ...

def draw_circle(window, x, y, radius, color, line):
    ...

def is_down(window, key, line):
    if key not in KEYS:
        raise _PlainError("I do not know that key.", line)      # reported the Plain way, 'try' can catch it
    return ...
```

- A function gets the thing first, then the values in the order of the `from python` line, and the **line number**
  of the Plain line last (to report mistakes at the right line).
- A field of a type that Python builds is the attribute of the class with the same name. `readonly` fields are
  often properties. Setting one is an error in Plain before the program runs.
- A Plain thing that arrives in Python (a `Color`) has its fields named `f_red`, `f_green`, `f_blue`.
- Numbers are Python floats, text is `str`, `true`/`false` are `bool`, lists are `list`.
- `raise _PlainError("message", line)` reports a problem the Plain way. `_FINISHERS.append(function)` runs a function
  when the program ends (the window module keeps the window on screen).
- The Python code is copied into every program (inside a function, so its names cannot clash with the program).
  Keep state in classes, do not use `global`.

The compiler, the checker, the hints, the IDE (highlighting) and the tests all learn the module from this one file,
so there is nothing else to register.
