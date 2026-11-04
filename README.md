<h1 align="center">Plain</h1>

<p align="center">
  <strong>A programming language that reads like English.</strong><br>
  Made for beginners and schools. Compiles to native machine code.
</p>

<p align="center">
  <a href="https://github.com/F02K/Plain/actions/workflows/ci.yml"><img alt="tests" src="https://github.com/F02K/Plain/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="status" src="https://img.shields.io/badge/status-MVP-orange">
  <img alt="targets" src="https://img.shields.io/badge/targets-Linux%20x64%20%7C%20Windows%20x64-blue">
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-Apache%202.0%20%2B%20Commons%20Clause-green"></a>
</p>

---

```
define Player as
    health as number
    score as number
end

action heal(player, amount) do
    set health of player to health of player + amount
end

let name be input "What is your name?"
let hero be Player(health: 80, score: 0)

heal(hero, 20)
say name + " has " + health of hero + " health."
```

## Why Plain?

| | |
| --- | --- |
| **Readable** | Keywords are English words: `if`, `then`, `while`, `do`, `end`. |
| **Nothing hidden** | No implicit conversions, no hidden allocations, no virtual machine, no garbage collector. |
| **Hard to get wrong** | `let` creates a variable, `set` changes it, and `=` only ever *compares* - the classic `=` / `==` mistake cannot happen. |
| **Friendly errors** | Messages show the line, point at the problem and suggest a fix. |
| **Real and fast** | Plain compiles to x64 assembly, then to a normal executable. It can also be translated to Python. Students can read the generated code. |

## Install

You need **Python 3.10+**. For native executables you also need **NASM** and a C compiler for linking (not needed for the Python backend).

<details open>
<summary>Linux (Debian / Ubuntu)</summary>

```
sudo apt install nasm gcc python3
git clone https://github.com/F02K/Plain.git && cd Plain
```
</details>

<details>
<summary>Windows</summary>

Install Python, [NASM](https://www.nasm.us/) and [MinGW-w64](https://www.mingw-w64.org/) (gcc), put them on your `PATH`, then clone the repository.
The test-suite runs on Windows in CI (native executables built with NASM and MinGW-w64).
</details>

Optional: `pip install .` adds a `plain` command. Otherwise use `python3 -m plain`.

## Usage

```
plain run examples/hello.plain                  # compile and run
plain build examples/game.plain -o game         # produce an executable
plain build game.plain --target windows         # cross-target (needs MinGW)
plain asm examples/game.plain                   # only write the assembly (.asm)
plain python examples/game.plain -o game.py     # translate to a standalone Python file
plain run examples/game.plain --backend python  # translate to Python and run it
```

Plain has two backends. Both use the same type checker and give the same results.

| Backend | Output | Needs |
| --- | --- | --- |
| native (default) | x64 assembly -> executable | NASM + gcc |
| python | a standalone `.py` file | Python only |

The Python backend is handy where NASM is not available (for example on a school
computer) and for reading the translation of a program.

## A quick tour

```
note: Variables
let health be 100
set health to health - 5

note: Decisions and loops
if health < 20 then
    say "careful!"
end

repeat 3 times
    say "tick"
end

note: Lists
let scores be list of number
add 10 to scores
add 20 to scores
for each score in scores do
    say score
end

note: Errors can be caught
try
    say 10 / 0
catch error then
    say "Problem: " + error
end
```

More: [`examples/`](examples/) and the full [language reference](docs/language.md).

## Documentation

| Document | Content |
| --- | --- |
| [Getting started](docs/getting-started.md) | Your first programs, step by step |
| [Language reference](docs/language.md) | Every statement, type and operator |
| [Error messages](docs/errors.md) | The errors you will meet and how to fix them |
| [Compiler internals](docs/compiler.md) | Architecture, value model, roadmap |
| [Contributing](CONTRIBUTING.md) | Development setup and tests |

## Project status

Plain is an **MVP**. The core language works and is tested in CI on Linux x64 and Windows x64.
Graphics, a standard library and more text/number functions are on the [roadmap](docs/compiler.md#roadmap).

## Repository layout

```
plain/       the compiler (lexer, parser, code generator, runtime, CLI)
examples/    example programs
tests/       test runner, run-cases and error-cases
docs/        documentation
```

## License

Plain is **free to use, study, modify and share**, but it may **not be sold**.
The license is [Apache 2.0 with the Commons Clause](LICENSE).

**Programs you create with Plain are yours** and may be sold or licensed however
you like: see the [Output Exception](LICENSE-EXCEPTION.md).

Note: because selling is restricted, Plain is *source-available* rather than
"open source" in the strict sense of the Open Source Initiative.

Copyright (c) 2026 F02K
