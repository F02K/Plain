# How the compiler works

```
source -> lexer -> parser -> code generator -> NASM assembly -> nasm -> gcc (link) -> executable
```

| File | Job |
| --- | --- |
| `plain/lexer.py` | text -> tokens |
| `plain/parser.py`, `plain/nodes.py` | tokens -> syntax tree |
| `plain/typesys.py` | the types |
| `plain/codegen.py` | type checking and assembly generation |
| `plain/runtime_asm.py` | the small assembly runtime (text, lists, errors) |
| `plain/pygen.py`, `plain/pyruntime.py` | the Python backend and its helper code |
| `plain/toolchain.py` | runs `nasm` and the linker |
| `plain/cli.py` | the `plain` command |
| `plain/errors.py` | friendly error messages |

## Backends

```
                              +--> codegen.py -> NASM -> executable   (native)
source -> lexer -> parser ----+
                              +--> pygen.py   -> standalone .py       (python)
```

The Python backend runs the native code generator first, only to type check, so
both backends accept and reject the same programs and show the same error messages.
Python uses its own dynamic types at run time; numbers are always floats, and
the helpers in `pyruntime.py` reproduce the native number formatting and error
messages. The test-suite runs every program on both backends.

## Design (native backend)

- Every value is one 64-bit slot: numbers are doubles, booleans 0/1, text a pointer to a
  zero-terminated string, a thing a pointer to its fields, a list a pointer to `[size, capacity, data]`.
- Types are inferred. Actions are compiled once per combination of argument types, so
  there is no run-time type information.
- `try` is implemented with a small stack of recovery points (stack pointer, frame
  pointer, catch address) - no `setjmp`, so Windows and Linux behave the same.
- Memory is never freed (no garbage collector). Fine for lessons and small programs.
- The C library is used only for operating-system services (printing, reading a line, memory).
- Windows x64 and Linux x64 (System V) differ only in the register names used for
  runtime calls (see the macros `A1`..`A4`) and a few call details.

## Status

- Linux x64: built and tested.
- Windows x64: assembly is generated and assembles with `nasm -f win64`; linking needs MinGW-w64.
  Not yet run on a real Windows machine.

## Roadmap

1. Run the test-suite on Windows in CI.
2. Window/graphics support (SDL2 or raylib through `extern` declarations).
3. Standard library: `Math`, `String`, `Window`, `Input`, `Draw`.
4. More text operations (length, parts of a text, upper case).
5. Sample project: a Pong-level 2D game.
6. Optimizations (keep values in registers, constant folding).
7. Open design questions: explicit program entry point, multiple return values, inheritance.
