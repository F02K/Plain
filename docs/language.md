# Plain language reference

A complete description of Plain. New to the language? Start with [Getting started](getting-started.md).

**Contents:** Types - Comments - Variables - Operators - Control flow - Actions - Things - Lists - Output and input - Built-in helpers - Modules - Errors - Reserved words

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

## Operators

| Precedence | Operators |
| --- | --- |
| 1 (highest) | `( )` |
| 2 | `*` `/` `mod` |
| 3 | `+` `-` |
| 4 | `=` `<` `>` `<=` `>=` |
| 5 | `not` |
| 6 (lowest) | `and`, `or` |

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
```

`stop` leaves the innermost loop, `skip` jumps to its next round.

## Actions (functions)

```
action heal takes(player, amount) do
    set health of player to health of player + amount
end

do heal(hero, 20)
```

- Without values write just `action greet do`, and run it with `do greet()`.
- `do` always means: run the code of an action. A line that runs an action starts with `do`
  (`do heal(hero, 20)`). Inside an expression an action that returns a value needs no `do`:
  `let total be add(1, 2)`.
- Parameters have no type annotations. The compiler works out the types from the
  calls and compiles one version of the action for each combination of types.
- `return value` gives a value back. Without `return`, an action gives back `nothing`.
- An action always returns the same type.
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

All fields must be given when creating a thing. Field types: `number`, `text`,
`boolean`, `list of ...` or another defined type.

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
| `upper of text` / `lower of text` | text in capitals / small letters (only a-z change) | `upper of name` |
| `round of number` | nearest whole number (.5 rounds up) | `round of 2.5` is `3` |
| `abs of number` | the number without its sign | `abs of -7` is `7` |
| `sqrt of number` | square root (negative numbers are an error) | `sqrt of 16` is `4` |

`of` binds tighter than the operators, so `round of x / 2` means `(round of x) / 2`.
Write `round of (x / 2)` to round the result.

Helpers with more values use brackets:

| Helper | Gives | Example |
| --- | --- | --- |
| `random(low, high)` | a random whole number from `low` to `high` (both included) | `random(1, 6)` |
| `min(a, b)` / `max(a, b)` | the smaller / bigger number | `max(health, 0)` |
| `part(text, start, count)` | `count` characters from position `start` (first is 0) | `part("Hello", 1, 3)` is `ell` |
| `contains(text, piece)` | `true` if `piece` is inside `text` (also `contains(list, value)`) | `contains(name, "an")` |

These names cannot be used for your own actions or types. A thing may still have a field
called `length` and so on: `length of box` reads the field when `box` is a thing.

## Modules

Extras that are not part of the language itself come as modules. A program asks for them with `import` in its
first lines:

```
import window

open window "My game" with width 640 and height 480
while window is open do
    clear window with color black
    use color orange
    draw circle at 320, 240 radius 30
    show window
end
```

The only module so far is `window` (windows, drawing, keys and mouse). Its sentences, the colors and how to write
your own module are in [Modules](modules.md).

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

## Reserved words

`let be set to say input if then else end repeat times while do for each in stop skip
action return define as list of at add remove from sort try catch import and or not mod true
false nothing` (`note:` starts a comment).

## Differences from the first draft of the specification

Small additions needed to make real programs possible: `not`, `mod`,
`set list at i to ...`, `input` (instead of `ask`), the error message in `catch name then`, and `\n`-style
escapes in text.
