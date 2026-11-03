# Plain language reference

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
action heal(player, amount) do
    set health of player to health of player + amount
end

heal(hero, 20)
```

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
```

## Output and input

```
say "Hello"                    note: prints with a new line
let name be ask "Your name?"   note: reads one line of text
```

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

`let be set to say ask if then else end repeat times while do for each in stop skip
action return define as list of at add remove from try catch and or not mod true
false nothing` (`note:` starts a comment).

## Differences from the first draft of the specification

Small additions needed to make real programs possible: `not`, `mod`,
`set list at i to ...`, the error message in `catch name then`, and `\n`-style
escapes in text.
