# How Plain works

```
source -> lexer -> parser -> checker -> Python writer -> a standalone .py file
                      ^
                      +-- modules/NAME/NAME.plain  (the sentences of `import NAME`)
```

Plain is Python, made simpler: a Plain program is checked, translated to a normal Python file and run by Python.
It has its own character (`let` / `set` / `be`, `end`, English sentences), but everything underneath is Python,
so it runs wherever Python runs.

| File | Job |
| --- | --- |
| `plain/lexer.py` | text -> tokens |
| `plain/parser.py`, `plain/nodes.py` | tokens -> syntax tree |
| `plain/modules.py` | reads `modules/NAME/NAME.plain`: the sentences, types and colors of a module |
| `plain/typesys.py` | the types |
| `plain/checker.py` | finds mistakes (types, unknown names, wrong number of values) before the program runs |
| `plain/pygen.py`, `plain/pyruntime.py` | writes the Python program and the helper code that goes into every program |
| `plain/toolchain.py` | check + translate in one call |
| `plain/cli.py` | the `plain` command |
| `plain/errors.py` | friendly error messages |
| `modules/` | modules such as `window` (see [Modules](modules.md)) |

## The checker

Plain has no type annotations, so the checker works out the types itself. An action is checked once for each
combination of argument types it is called with (like a template). A program that passes the checker cannot
mix up numbers, text and lists, and Python never sees a program with such a mistake.

Python uses its own types at run time; numbers are always floats, and the helpers in `pyruntime.py` print them the
Plain way and turn run-time problems (division by zero, a list position that does not exist, ...) into friendly
messages with the line number.

## The IDE

The IDE (`ide/plainide/`) runs the translation with two extras that are switched on only when you ask for them:

- *Live values* and *Value list*: `compile_to_python(source, watch=True)` adds small hooks after assignments,
  conditions, calls and `return`. A background thread writes the latest values to a file a few times per second
  and the IDE shows them behind the code.
- Clicking a name explains it (`ide/plainide/symbols.py`), working on the text only.

## Roadmap

1. More modules: `sound`, `random` helpers, `file`, `web`. A module is a small folder; see [Modules](modules.md).
2. Sprites and images for the `window` module.
3. A package manager-like way to share modules between classes.
4. Open design questions: explicit program entry point, multiple return values, inheritance.
