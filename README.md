# Plain

**Plain** is a programming language that reads like simple English. It is designed
for beginners and schools, and it compiles straight to native machine code
(through x64 assembly) - no virtual machine, no garbage collector, no hidden magic.

```
define Player as
    health as number
    score as number
end

action heal(player, amount) do
    set health of player to health of player + amount
end

let hero be Player(health: 80, score: 0)
heal(hero, 20)
say "Health: " + health of hero
```

## Principles

- **Nothing is hidden.** No implicit conversions, no hidden allocations.
- **One way per concept.** One clear syntax for each task.
- **English keywords** (`if`, `then`, `while`, `do`, `end`) and normal math symbols.
- **`let` creates, `set` changes.** `=` only ever means *compare*, so the classic `=` / `==` mix-up cannot happen.
- **Friendly error messages** that point at the problem and suggest a fix.

## Quick start

Requirements: Python 3.10+, [NASM](https://www.nasm.us/) and `gcc` (Linux), or
NASM and MinGW-w64 `gcc` (Windows).

```
python3 -m plain run examples/hello.plain
python3 -m plain build examples/game.plain -o game
python3 -m plain asm examples/game.plain        # write the generated assembly
```

Targets: `--target linux` (default on Linux) and `--target windows`.

## Documentation

- [Language reference](docs/language.md)
- [How the compiler works](docs/compiler.md)
- [Examples](examples/)

## Status

This is the MVP. See the roadmap in [docs/compiler.md](docs/compiler.md).

## Tests

```
python3 tests/run_tests.py
```

## License

See [LICENSE](LICENSE).
