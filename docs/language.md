# Plain language reference

A complete description of Plain. New to the language? Start with [Getting started](getting-started.md).

**Contents:** Types - Comments - Variables - Operators - Control flow - Actions - Things - Lists - Text - Waiting and files - Output and input - Built-in helpers - Modules and your own files - Errors - Reserved words

## Types

| Type | Meaning | Example |
| --- | --- | --- |
| `number` | integers and decimals | `1`, `1.5`, `-3` |
| `text` | a string | `"Hello"` |
| `boolean` | truth value | `true`, `false` |
| `list of X` | list of values of one type | `list of number` |
| `nothing` | no value | `return nothing` |

There is no separate `int`/`float`. Numbers print with up to 15 significant digits.
Text supports the escapes `\n`, `\t`, `\"` and `\\`.

## Comments

```
note: This is a comment
```

## Variables

```
let health be 100          note: create
set health to health - 5   note: change
```

Variables are only visible inside the block (and the action) where they are created.
Actions cannot see variables of the main program: pass values in as parameters.
Creating a variable with a name that already exists is an error.

### Fixed values

Put `fixed` at the end of a `let` line to make a value that can never be changed:

```
let pi be 3.14159 fixed
let max_health be 100 fixed
let title be "Space Game" fixed

action area takes(radius) do
    return pi * radius * radius       note: a top-level fixed value is known inside actions
end

set pi to 3                           note: Error: 'pi' is fixed, so it cannot be changed.
```

- A fixed name cannot be changed in any way: no `set`, and for a list or a thing no `add`, `remove`, `sort`,
  `set list at ...` or `set field of ...` through that name.
- A `let ... fixed` line at the top level of the program (not inside an `if`, a loop or an action) whose value is made of
  numbers, text, `true`/`false` and other fixed values (`let tau be pi * 2 fixed`) is known **everywhere**, also in
  actions and in imported files. It is made before the program starts, so it can be used on any line.
- Any other `let ... fixed` is only read-only where it is made (for example `let name be input "Name?" fixed`).
- A fixed value cannot share its name with a parameter or another variable.

## Operators

| Precedence | Operators |
| --- | --- |
| 1 (highest) | `( )` |
| 2 | `*` `/` `mod` |
| 3 | `+` `-` |
| 4 | `=` `<` `>` `<=` `>=` |
| 5 | `not` |
| 6 (lowest) | `and`, `or` |

- Numbers are written in full: `20!` is `2432902008176640000`, and `1 / 10000000` is `0.0000001`.
- `mod` follows the divisor, like in maths: `7 mod 3` is `1`, `-7 mod 3` is `2`, `7 mod -3` is `-2`.
- `=` compares (numbers, text, booleans; things and lists compare identity).
- `+` adds numbers or joins text. If one side is text, the other side (number or boolean) is turned into text.
- `and` and `or` cannot be mixed without parentheses: `(a and b) or c`.
- Comparisons cannot be chained: write `a < b and b < c`.

## Control flow

```
if health <= 0 then
    say "dead"
else if health < 20 then
    say "careful"
else
    say "fine"
end

repeat 5 times
    say "tick"
end

while health > 0 do
    set health to health - 1
end

for each enemy in enemies do
    if alive of enemy = false then
        skip          note: like "continue"
    end
    say name of enemy
end

for i from 1 to 10 do          note: counts 1, 2, ... 10 (the end is included)
    say i
end

for i from 10 to 0 step -2 do  note: 10, 8, 6, 4, 2, 0
    say i
end

for each letter in "abc" do    note: a text is walked letter by letter
    say letter
end
```

`stop` leaves the innermost loop, `skip` jumps to its next round.

A counting loop `for i from a to b` runs `i` from `a` to `b` in steps of 1; nothing happens when `a` is already past `b`.
Add `step` to count in other steps (`step 2`, `step 0.5`) or downwards (`step -1`). The step cannot be 0.
`step` is only a special word inside a `for` line, so it still works as a name of your own.

## Actions (functions)

```
action heal takes(player, amount) do
    set health of player to health of player + amount
end

run heal(hero, 20)
```

- Without values write just `action greet do`, and run it with `run greet()`.
- The thing an action works on can be written after `of`, as its first value: `run heal(20) of hero` is the same as
  `run heal(hero, 20)`, and `run show of window` is `run show(window)`. It works in expressions too:
  `if is_down("left") of win then`.
- Values can be given with their names, in any order, after the plain values: `heal(hero, amount: 20)`,
  `area(h: 3, w: 4)`. A value cannot be given twice.
- `run` always means: run the code of an action. A line that runs an action starts with `run`
  (`run heal(hero, 20)`). Inside an expression an action that returns a value needs no `run`:
  `let total be add(1, 2)`.
- Parameters have no type annotations. The compiler works out the types from the
  calls and compiles one version of the action for each combination of types.
- `return value` gives a value back. Without `return`, an action gives back `nothing`.
- An action always returns the same type.
- If an action gives back a value somewhere, every way through it must end with a `return`
  (put one at the very end, or an `else` branch that returns). Plain tells you when one is missing.
- An action that is never called is still checked, so a mistake in it shows up at once and not only when you use it.
- Recursion is allowed; put the base-case `return` before the recursive call.

## Things (structs)

```
define Player as
    x as number
    y as number
    health as number
end

let hero be Player(x: 0, y: 0, health: 100)
say health of hero
set health of hero to 90
```

All fields must be given when creating a thing, unless the field has a value for when none is given:

```
define Settings as
    volume as number = 5
    name as text = "player"
end

let s be Settings(name: "Eve")      note: volume is 5
let t be Settings()                 note: all defaults
```

Field types: `number`, `text`, `boolean`, `list of ...` or another defined type.

## Lists

```
let enemies be list of Enemy
add Enemy(x: 3, y: 0, damage: 15, alive: true) to enemies
remove enemy from enemies      note: removes the first match
say size of enemies
say enemies at 0               note: positions start at 0
set enemies at 0 to other
remove at 0 from enemies       note: removes the item at that position
sort scores                    note: smallest first (numbers or text)
say contains(scores, 10)       note: true if the list has that value
```

`sort` works on lists of numbers and lists of text. `contains` also works on text
(see Built-in helpers). Using a position that does not exist is an error.

## Text

A text is a row of letters; the first letter is at position 0.

```
let word be "plain"
say word at 0                       note: p
say length of word                  note: 5
for each letter in word do
    say upper of letter
end

let parts be split("red,green,blue", ",")     note: a list of text
say join(parts, " and ")                      note: red and green and blue
say replace("a-b-c", "-", "+")                note: a+b+c
say number of "42" + 1                        note: 43   (text -> number)
say "Score: " + text of 42                    note: 42 becomes text (a number is also joined to text by +)
```

- A text cannot be changed letter by letter. Build a new one: `set word to part(word, 0, 2) + "x"`.
- `number of text` reads a number from a text, like `input number` does; anything else is the error `That is not a number.`
  (catch it with `try`).
- `split(text, "")` splits into single letters; `join` needs a list of text.

## Waiting and files

```
say "Ready..."
wait 2 seconds                         note: also: wait 1 second, wait 0.5 seconds, wait pause
say "Go!"

run write_file("scores.txt", "Ada: 10\nMax: 7\n")      note: makes or replaces the file
run append_file("scores.txt", "Eve: 9\n")               note: adds at the end
if file_exists("scores.txt") then
    let lines be split(trim of read_file("scores.txt"), "\n")      note: a list of text, one item per line
    for each line in lines do
        say line
    end
end
```

- `wait` pauses the program for that many seconds (a number, not negative).
- Files are text files (UTF-8). A path without a folder means "next to the program" - the IDE runs a program in its own
  folder. A file that does not exist is the error `The file 'x' does not exist.` (catch it with `try`).
- `write_file` and `append_file` are things you *do*, so they start with `run`, like an action.
- The list of helpers is in [Built-in helpers](#built-in-helpers).

## Output and input

```
say "Hello"                      note: prints with a new line
let name be input "Your name?"   note: asks, then reads one line of text
```

`say` accepts text, numbers and booleans. `input` prints the question, waits for
the user to type a line, and gives it back as `text` (without the line break).

To read a number, write `input number`:

```
let age be input number "How old are you?"
say "Next year you will be " + (age + 1)
```

If the user types something that is not a number (only digits, `.`, `-`, `+`, `e`
and spaces are accepted), the program stops with the error `That is not a number.`
Catch it with `try` to ask again:

```
let age be 0
let ok be false
while not ok do
    try
        set age to input number "Your age?"
        set ok to true
    catch error then
        say "Please type a number."
    end
end
```

## Built-in helpers

Helpers with one value are written `name of value`, like fields:

| Helper | Gives | Example |
| --- | --- | --- |
| `length of text` | number of characters | `length of "héllo"` is `5` |
| `upper of text` / `lower of text` | text in capitals / small letters (umlauts too; `ß` stays) | `upper of name` |
| `round of number` | nearest whole number (halves go away from zero) | `round of 2.5` is `3`, `round of -2.5` is `-3` |
| `abs of number` | the number without its sign | `abs of -7` is `7` |
| `sqrt of number` | square root (negative numbers are an error) | `sqrt of 16` is `4` |
| `trim of text` | the text without spaces and line breaks at both ends | `trim of "  hi "` is `hi` |
| `number of text` | the number in a text (an error when it is not a number) | `number of "3.5"` is `3.5` |
| `text of value` | a number or boolean as text | `text of 42` is `42` |

`of` binds tighter than the operators, so `round of x / 2` means `(round of x) / 2`.
Write `round of (x / 2)` to round the result.

Helpers with more values use brackets:

| Helper | Gives | Example |
| --- | --- | --- |
| `random(low, high)` | a random whole number from `low` to `high` (both included) | `random(1, 6)` |
| `min(a, b)` / `max(a, b)` | the smaller / bigger number | `max(health, 0)` |
| `part(text, start, count)` | `count` characters from position `start` (first is 0) | `part("Hello", 1, 3)` is `ell` |
| `contains(text, piece)` | `true` if `piece` is inside `text` (also `contains(list, value)`) | `contains(name, "an")` |
| `index_of(text, piece)` | position of the first `piece` in `text`, or `-1` | `index_of("Hello", "ll")` is `2` |
| `starts_with(text, piece)` / `ends_with(text, piece)` | `true` if the text begins / ends with `piece` | `ends_with("a.plain", ".plain")` |
| `replace(text, old, new)` | every `old` replaced by `new` | `replace("a-b", "-", "+")` is `a+b` |
| `split(text, separator)` | a list of text; the separator `""` gives the letters | `split("a,b", ",")` |
| `join(list, separator)` | the items of a list of text as one text | `join(words, ", ")` |
| `read_file(path)` | the whole text of a file | `read_file("scores.txt")` |
| `file_exists(path)` | `true` if the file exists | `file_exists("scores.txt")` |
| `run write_file(path, text)` / `run append_file(path, text)` | make or replace a file / add text at its end | `run write_file("a.txt", "Hi")` |

These names cannot be used for your own actions or types. A thing may still have a field
called `length` and so on: `length of box` reads the field when `box` is a thing.

## Modules and your own files

Extras that are not part of the language itself come as modules. A program asks for them with `import` in its
first lines:

```
import window

import color

let win be Window(title: "My game", width: 640, height: 480)
while open of win do
    run clear of win
    run draw_circle(320, 240, 30, orange of color) of win
    run show of win
end
```

The built-in modules are `window` (windows, drawing, keys and mouse) and `color` (the type `Color` and the color names;
`window` brings it in). Its things, actions, the colors and how
to write your own module are in [Modules](modules.md). A module is a Plain file like your own, so everything below
about your own files holds for modules too.

**Your own files.** A big program can be split into several files. `import name` brings in the actions and types of
`name.plain`, which lies in the same folder as your program (the IDE also looks in the project folder):

```
note: shapes.plain - a library: it may only hold import, define and action
define Point as
    x as number
    y as number
end

action distance takes(a, b) do
    return sqrt of ((x of a - x of b) * (x of a - x of b) + (y of a - y of b) * (y of a - y of b))
end
```

```
note: main.plain
import shapes

say distance(Point(x: 0, y: 0), Point(x: 6, y: 8))      note: 10
```

- The types and actions of an imported file are used as if they were written in your program; all names are
  shared, so a name can be used only once (Plain tells you where the first one is).
- A file sees only what it imports itself. If `lib_a` imports `lib_b`, your program has to write `import lib_b`
  too before it can use the names of `lib_b`.
- The fixed values of an imported file are reached through its name: `gravity of lib_constants` (see below)
- A file can import other files, but not in a circle. Every file is read once.
- If the mistake is inside the imported file, the message shows that file and line (the IDE opens it).
- An imported file may also hold `let ... fixed` values (a library of constants). They are written `name of file`
  in the program and in its actions, for example `gravity of lib_constants`. Inside the file itself the plain name works.
- The imports go in the first lines. A built-in module wins over a file with the same name.
- Modules are used in the same way: `import color`, then `orange of color`.

## Errors

```
try
    set result to 10 / divisor
catch error then
    say "Problem: " + error
end
```

`catch <name> then` gives the error message as a `text` in the variable you name.
Without `try`, a runtime error stops the program with the line number and a reason.

Make an error of your own with `fail` and a text:

```
action heal takes(health, amount) do
    if amount < 0 then
        fail "Healing cannot be negative."
    end
    return health + amount
end

try
    say heal(50, -5)
catch error then
    say "Problem: " + error          note: Problem: Healing cannot be negative.
end
```

`fail` stops the action and the program at that line, just like a built-in error
(`Error in line 3: Healing cannot be negative.`), unless a `try` around it catches it.
An action that ends with `fail` on some way does not need a `return` there.

## Reserved words

`let be set to say input if then else end repeat times while do for each in stop skip
action run return fail define as list of at add remove from sort try catch import and or not mod true
false nothing` (`note:` starts a comment).

`takes`, `step` and `fixed` are only special in the place where they belong, so they still work as names of your own.

The built-in helpers (`length`, `upper`, `lower`, `round`, `abs`, `sqrt`, `trim`, `number`, `text`, `random`, `min`,
`max`, `part`, `contains`, `index_of`, `starts_with`, `ends_with`, `replace`, `split`, `join`, `read_file`, `write_file`,
`append_file`, `file_exists`) cannot be used as names of your own actions or types. `wait` is only special at the start of
a line, so it still works as a name of your own.
