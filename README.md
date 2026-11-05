<h1 align="center">Plain</h1>

<p align="center">
  <strong>A programming language that reads like English.</strong><br>
  Made for beginners and schools. Python, but simpler.
</p>

<p align="center">
  <a href="https://github.com/F02K/Plain/actions/workflows/ci.yml"><img alt="tests" src="https://github.com/F02K/Plain/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="status" src="https://img.shields.io/badge/status-MVP-orange">
  <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-Apache%202.0%20%2B%20Commons%20Clause-green"></a>
</p>

---

```
define Player as
    health as number
    score as number
end

action heal takes(player, amount) do
    set health of player to health of player + amount
end

let name be input "What is your name?"
let hero be Player(health: 80, score: 0)

run heal(hero, 20)
say name + " has " + health of hero + " health."
```

## Why Plain?

| | |
| --- | --- |
| **Readable** | Keywords are English words: `if`, `then`, `while`, `do`, `end`. |
| **Hard to get wrong** | `let` creates a variable, `set` changes it, and `=` only ever *compares* - the classic `=` / `==` mistake cannot happen. |
| **Checked before it runs** | Plain finds type mistakes before the program starts and explains them in plain words. |
| **Friendly errors** | Messages show the line, point at the problem and suggest a fix. |
| **Python underneath** | A Plain program is checked and translated to a normal Python file that students can read. It runs everywhere Python runs. |
| **Modules** | Extras such as windows and drawing are modules: `import window`. A module says in one small file which sentences it adds. |

## Install

You need **Python 3.10+**. Nothing else.

```
git clone https://github.com/F02K/Plain.git
cd Plain
```

On Windows use `python` (or `py`) instead of `python3`.
Optional: `pip install .` adds a `plain` command. For an editor that looks like VS Code (project Explorer, tabs, Run button, live values; handy in classrooms) see [`ide/`](ide/README.md). Otherwise use `python3 -m plain`.

## Usage

```
plain run examples/hello.plain                  # check, translate and run
plain python examples/game.plain -o game.py     # only write the Python file
```

## Modules

Windows and drawing are not part of the language itself. A program asks for them at the top:

```
import window

open window "My game" with width 480 and height 320
while window is open do
    clear window with color black
    use color orange
    draw circle at 240, 160 radius 30
    show window
end
```

Every module lives in `modules/NAME/`: a `NAME.plain` file lists its sentences, a `NAME.py` file does the work.
See [Modules](docs/modules.md).

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
| [Modules](docs/modules.md) | `import`, the window module, how to write a module |
| [How it works](docs/compiler.md) | Architecture and roadmap |
| [Contributing](CONTRIBUTING.md) | Development setup and tests |

## Project status

Plain is an **MVP**. The core language works and is tested in CI on Linux and Windows.
Windows and drawing work as a module (see [`examples/ball.plain`](examples/ball.plain)); more modules are on the [roadmap](docs/compiler.md#roadmap).

## Repository layout

```
plain/       the compiler (lexer, parser, checker, Python writer, CLI)
modules/     modules such as window (a .plain file with the sentences, a .py file with the code)
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
