# Getting started

This guide takes you from "Hello, world!" to a small game in a few steps.
Setup is described in the [README](../README.md#install).

## 1. Hello, world

Create a file `hello.plain`:

```
say "Hello, world!"
```

Run it:

```
plain run hello.plain
```

`say` prints a line. Lines that start with `note:` are comments for humans.

## 2. Variables

```
let name be "Max"
let age be 12
say name + " is " + age + " years old."

set age to age + 1
say "Next year: " + age
```

- `let` **creates** a variable, `set` **changes** it.
- `+` joins text. Numbers and booleans are turned into text automatically when joined.

## 3. Asking the user

```
let name be input "What is your name?"
say "Hello, " + name
```

`input` shows the question, waits for the user to type a line and press Enter,
and gives the line back as `text`.

To read a number, use `input number`:

```
let age be input number "How old are you?"
say "Next year: " + (age + 1)
```

## 4. Decisions

```
let temperature be 25

if temperature > 30 then
    say "hot"
else if temperature > 15 then
    say "nice"
else
    say "cold"
end
```

Compare with `=`, `<`, `>`, `<=`, `>=`. Combine with `and`, `or`, `not`.

## 5. Loops

```
repeat 3 times
    say "Hip hip hooray"
end

let i be 1
while i <= 5 do
    say i
    set i to i + 1
end
```

When you know how often to count, a counting loop is shorter:

```
for i from 1 to 5 do
    say i
end

for i from 10 to 0 step -2 do      note: counting down needs a negative step
    say i
end
```

The end is included. Use `stop` to leave a loop early and `skip` to jump to the next round.

## 6. Actions

An action is a reusable piece of code.

```
action square takes(n) do
    return n * n
end

say square(7)
```

## 7. Working with text

```
let word be "plain"
say word at 0                          note: p  (the first letter is at position 0)
for each letter in word do
    say upper of letter
end

let colors be split("red,green,blue", ",")
say join(colors, " and ")
say number of "20" + 1                 note: 21  (a text made of a number becomes a number)
```

## 8. Your own types and lists

```
define Enemy as
    name as text
    health as number
end

let enemies be list of Enemy
add Enemy(name: "Slime", health: 10) to enemies
add Enemy(name: "Bat", health: 6) to enemies

for each enemy in enemies do
    say name of enemy + ": " + health of enemy
end
```

## 9. A complete program

See [`examples/game.plain`](../examples/game.plain) for a small game simulation
that uses types, lists, actions and loops together.

## What next?

- Read the [language reference](language.md).
- Made a mistake? Look it up in [Error messages](errors.md).
