# Contributing

## Setup

```
sudo apt install nasm gcc python3
python3 tests/run_tests.py
```

No other dependencies - the compiler uses only the Python standard library.

## Tests

- `tests/cases/NAME.plain` + `NAME.out` (+ optional `NAME.in` as keyboard input): the program is compiled, run, and its output compared.
- `tests/errors/NAME.plain` + `NAME.err`: compilation must fail; every line of `NAME.err` must appear in the error message.

Add a test with every new feature or fix. CI runs the same suite.

## Code layout

See [docs/compiler.md](docs/compiler.md). Code, comments, messages and docs are written in English.

## Style

- Keep the language small: one clear way per concept.
- Error messages are part of the product: say what is wrong, where, and how to fix it.
