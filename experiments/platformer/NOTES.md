# Platformer experiment: what a bigger Plain program needs

`platformer.plain` is a small side scroller (scrolling level, jumping, coins, patrolling enemies, a goal flag,
lives, save and load). Run it with `python -m plain run experiments/platformer/platformer.plain`
(arrow keys, up/space jump, S save, L load, R restart).

It compiled on the first try and ran headless with scripted keys (save file written, coins collected, lives lost).
It was written with only today's language, on purpose, to see where it hurts.

## What worked well

- `let ... fixed` values are visible inside actions: `tile`, `gravity`, `player_w` need no passing around.
- Counting loops, `stop`, `try`/`catch` and `fail` made physics and loading short and readable.
- Things (`Player`, `Enemy`) as plain data, actions that take them, `run move_player(hero, level)`.

## Where it hurts

| # | Problem | Where | Idea |
| --- | --- | --- | --- |
| 1 | Saving is hand-made text: `"x=" + x of p + "\n"`, then `split`, `number of`, an if-chain on the key, `-1` as "missing" | `save_game`, `load_game` (about 70 lines) | save/load whole things, see below |
| 2 | A level is a `list of text`; changing one tile means rebuilding the row with `part` | `collect_coins` | `grid of text`, or `replace_part(text, start, count, new)` |
| 3 | Emptying a list needs a loop | `clear_list` | `run clear(list)` |
| 4 | Rounding down is `(v - v mod tile) / tile` | `cell` | `floor of x`, `ceil of x` |
| 5 | "Pressed once" (save, load) needs two helper variables per key | main loop | `key "s" was pressed` (window module) |
| 6 | Actions cannot see main variables, so the parameter lists grow (`draw_world(level, cam)`) | everywhere | bundle the game state in one thing (`Game`) |
| 7 | `overlaps` takes eight numbers | `overlaps` | pass things with `x, y, width, height` instead |

Only 1 is about files. 6 and 7 are about how I wrote it, not the language.

## Files in Plain style

Rules for anything we wrap from Python (files, json, web, ...):

1. **Verbs are actions, questions are calls.** `run save(game, "slot1.save")`, `file_exists("slot1.save")`.
   Same shapes as `run write_file(...)` and `random(1, 6)` today.
2. **No handles.** Nothing is opened or closed and there is no `file.write()`. The action does open, work, close.
3. **Whole values.** A file is read or written as a whole: a text, a list of lines, or a thing.
4. **Only Plain types cross the border:** number, text, boolean, list, thing. Python objects never reach the program.
5. **Errors in Plain words, with `try`/`catch`:** `The file 'slot1.save' is not a Game: 'coins' is missing.`
6. **Main value first, details after:** `replace(text, old, new)`, `save(value, path)`.
7. **Python lives only in binding files** (a `.plain` file with `is python` actions plus its `.py`). A program is
   written in Plain only; it just calls the actions.

### Proposed helpers

Text files (small additions to what exists):

```
let lines be lines_of("scores.txt")             note: list of text, one item per line
run write_lines("scores.txt", lines)
run delete_file("old.sav")
let saves be files_in("saves")                  note: list of text
run make_folder("saves")
```

Things and lists, the part that replaces `save_game` and `load_game`:

```
run save(game, "slot1.save")                    note: a thing or a list, any depth
run load(game, "slot1.save")                    note: fills the existing thing; same type as the variable
```

`load` fills a variable that already exists, so no type has to be named in the call, and the checker knows the type.
A missing file, a broken file or a file for another type is an error with a clear message that `try` can catch.
The file is readable text (JSON underneath, so other programs can read it too).

The platformer then looks like this (not runnable yet):

```
define Game as
    hero as Player
    level as list of text
    enemies as list of Enemy
end

if s_pressed then
    run save(game, "slot1.save")
end
if l_pressed then
    try
        run load(game, "slot1.save")
    catch error then
        set message to error
    end
end
```

The 70 lines of `save_game` and `load_game` become two calls.

### How the Python side gets it without leaking

The binding file says what Plain sees; Python does the work:

```
note: modules/files/files.plain
using python "files_impl"

action save takes(value as anything, path as text) is python
action load takes(target as anything, path as text) is python
action lines_of takes(path as text) gives list of text is python
```

- `anything` is only allowed in binding files. For it the compiler adds the **shape** of the value (field names and
  types, recursively) as an extra argument, so Python can rebuild `Enemy` things and number types correctly:
  `def save(value, shape, path, line)`.
- Python errors are turned into Plain errors at the border (`raise PlainError("...", line)`).
- The same mechanism, written by anyone in their own `.plain` + `.py` pair, is how `using` can reach the long tail
  of Python later. The program that calls it stays pure Plain.

## Open questions

1. Is `save` / `load` the right pair of names, or `save_game`-like longer names? (Short names may collide with user actions.)
2. JSON on disk, or a small readable Plain-like format?
3. Should `load` also be allowed as `let game be load(...)` with a type argument? (Needs a type as a value.)
4. Where do saves live: next to the program (today's rule for files), or in a per-user folder?
