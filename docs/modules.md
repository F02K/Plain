# Modules

Not everything belongs in the language itself. Windows and drawing, for example, are a **module**.
A program asks for a module in the first lines:

```
import window

open window "Plain Ball" with width 480 and height 320
while window is open do
    ...
    show window
end
```

Without `import window` the sentences of the module do not exist. If you use one anyway, Plain tells you where it
comes from:

```
'open window' belongs to the module 'window', which is not imported.
Hint: Add this line at the very top of your program:  import window
```

`import` lines go at the very top, before everything else (comments are fine).

## The window module

Everything is written as a short sentence. Coordinates are numbers; `(0, 0)` is the top left corner,
`x` grows to the right and `y` grows downwards.

| Sentence | What it does |
| --- | --- |
| `open window "title" with width 640 and height 480` | opens the window (only one at a time) |
| `close window` | closes the window from the program |
| `show window` | shows what was drawn and waits for the next frame (about 60 per second) |
| `window is open` | `true` while the window is open (`false` after the user closed it) |
| `clear window` | fills the whole window with the current color |
| `clear window with color black` | the same, with a color |
| `use color orange` | sets the color for everything drawn next |
| `draw rectangle at x, y size 100 by 50` | a filled rectangle with its top left corner at `x, y` |
| `draw circle at x, y radius 20` | a filled circle around `x, y` |
| `draw line from x1, y1 to x2, y2` | a line |
| `draw text "Score" at x, y` | text with its top left corner at `x, y` |
| `key "left" is pressed` | `true` while the key is held down. Keys: `"left"`, `"right"`, `"up"`, `"down"`, `"space"`, `"enter"`, `"escape"`, `"shift"`, `"ctrl"`, `"tab"`, `"backspace"`, `"a"` to `"z"`, `"0"` to `"9"`. The key can also be a text variable. |
| `mouse x` / `mouse y` | where the mouse is inside the window |
| `mouse is down` | `true` while the left mouse button is held down |

### Colors

- Named colors: `red`, `green`, `blue`, `yellow`, `orange`, `purple`, `pink`, `brown`, `gray`, `white`, `black`.
  `use color orange`, `clear window with color black`. A name has to be at the end of its line.
- Your own colors are things of the type `Color` (it comes with the module) with the fields `red`, `green` and
  `blue` (0 to 255):

  ```
  let sky be Color(red: 20, green: 24, blue: 40)
  use color sky
  set red of sky to 100
  ```
- Three numbers work as well: `use color 255, 128, 0`.

### Things to know

- Drawing happens in the background; nothing appears until `show window`. Use `clear window` at the start of each
  picture, otherwise old drawings stay.
- Events (closing the window, keys) are handled inside `show window`, so call it in every round of your loop.
- When the program ends while the window is open, the window stays until it is closed.
- Drawing before `open window` is an error: `Open a window first`.
- The window uses tkinter, which comes with Python. Set the environment variable `PLAIN_HEADLESS=1` to keep
  windows hidden (used by the tests).
- See [`examples/ball.plain`](../examples/ball.plain).

## Writing a module

A module is a folder in `modules/` with two files that have the name of the folder:

```
modules/window/window.plain    which sentences the module adds
modules/window/window.py       the Python code that runs when a sentence is used
```

`window.plain` is read by the compiler. It is written in Plain's own style:

```
module window
python window.py

type Color
    red as number
    green as number
    blue as number
end

colors
    orange 255 150 30
end

command draw circle at <x: number = 200>, <y: number = 150> radius <radius: number = 30> = window_circle
question window is open gives boolean = window_is_open
question key <name: text = "left"> is pressed gives boolean = window_key_pressed
```

- `command` is a sentence that is a line of its own. `question` is a sentence that gives a value and is used inside
  other lines (`while window is open do`).
- Words are written as they are. `<x: number = 200>` is a value the programmer fills in: its name, its type
  (`text`, `number`, `boolean` or `color`) and an example that shows up in hints and error messages.
- `gives boolean` is the type of the answer of a question.
- After `=` comes the name of the Python function in `window.py`. It receives the values in order and, as the last
  value, the line number (to report mistakes at the right line):

  ```python
  def window_circle(x, y, radius, line):
      ...
  ```
  A `color` value arrives as three numbers. Raise `_PlainError("message", line)` to report a problem the Plain way.
- A module may add a `type` (like `Color`) and a table of `colors`.
- `_FINISHERS.append(function)` runs a function when the program ends (the window module keeps the window on screen).

The compiler, the checker, the hints, the IDE (highlighting) and the tests all learn the new sentences from this one
file, so there is nothing else to register.
