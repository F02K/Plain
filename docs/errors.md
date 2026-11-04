# Error messages

Plain explains problems in plain words. An error looks like this:

```
Error in game.plain, line 3:
    3 |     say secret
      |         ^
I don't know a variable called 'secret'.
Hint: An action only knows its own parameters and variables. Pass other values in as parameters.
```

## Compile-time errors (before the program runs)

| Message | Cause and fix |
| --- | --- |
| `I don't know a variable called 'x'.` | Typo, or the variable was never created. Create it with `let x be ...`. Inside an action only parameters and the action's own variables exist. |
| `Use 'be' to create a variable.` | You wrote `let x = 5`. Write `let x be 5`. |
| `Use 'to' to give a variable a new value.` | You wrote `set x = 5`. Write `set x to 5`. |
| `'==' is not used in Plain.` | To compare, use a single `=`. For "not equal" write `not (a = b)`. |
| `There is already a variable called 'x'.` | Names can only be created once. Use `set x to ...` to change it. |
| `The variable 'x' holds a number, but this value is a text.` | A variable keeps its type. Convert by joining: `"" + 5` gives text. |
| `This 'if' is never closed.` | A block is missing its `end`. |
| `'and' and 'or' are mixed here.` | Add parentheses: `(a and b) or c`. |
| `'+' needs two numbers ...` | Maths works on numbers only; `+` also joins text. |
| `'name' needs 2 value(s) ... but you gave 1.` | Wrong number of arguments in an action call. |
| `'P' has no field called 'y'.` | The hint lists the available fields. |
| `'stop' can only be used inside a loop.` | Move it into a `while`, `repeat` or `for each`. |
| `'end' is a reserved word ...` | Pick a different name; see the [reserved words](language.md#reserved-words). |
| `'ask' is now called 'input'.` | Use `input "question"`. |
| `I don't know yet what 'f' gives back ...` | A recursive action needs a `return` (the base case) before it calls itself. |

When an error happens inside an action, a note tells you which action and with which argument types it was compiled.

## Runtime errors (while the program runs)

```
Error in line 2: Cannot divide by zero.
```

| Message | Cause |
| --- | --- |
| `Cannot divide by zero.` | `/` with a divisor of 0. |
| `Cannot use mod with zero.` | `mod 0`. |
| `That is not a number.` | The user typed something else than a number at an `input number`. |
| `That list position does not exist ...` | Index outside the list; the first item is at position 0. |
| `The computer ran out of memory.` | Allocation failed. |

Catch runtime errors with `try ... catch error then ... end`; the message is available as text in the variable you name.
