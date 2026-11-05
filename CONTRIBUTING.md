# Contributing

## Setup

```
python3 tests/run_tests.py
```

On Windows use `python tests/run_tests.py`.

No other dependencies - the compiler uses only the Python standard library.

## Tests

- `tests/cases/NAME.plain` + `NAME.out` (+ optional `NAME.in` as keyboard input): the program is translated to Python, run, and its output compared.
- `tests/windows/NAME.plain` + `NAME.out`: like the above for the window module, with the window hidden (`PLAIN_HEADLESS=1`).
- `tests/errors/NAME.plain` + `NAME.err`: compilation must fail; every line of `NAME.err` must appear in the error message.

Add a test with every new feature or fix. CI runs the same suite.

## Code layout

See [docs/compiler.md](docs/compiler.md). Code, comments, messages and docs are written in English.

## Style

- Keep the language small: one clear way per concept.
- Error messages are part of the product: say what is wrong, where, and how to fix it.

## License of contributions

By submitting a contribution you agree that it is licensed under the same terms as the
project: Apache 2.0 with the Commons Clause and the Output Exception (see [LICENSE](LICENSE)
and [LICENSE-EXCEPTION.md](LICENSE-EXCEPTION.md)).

## Releases

Push a tag such as `v0.2.0` (or start the *release* workflow by hand on GitHub). It builds
`plain` and `PlainIDE` for Windows and Linux, packs them with the examples and docs, and
creates a **draft** release. Check the draft, then publish it.
To build locally: `pip install pyinstaller`, then `python ide/build.py` (the IDE) and `python packaging/build_cli.py` (the `plain` program).
