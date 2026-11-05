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
| `The action 'f' gives back a number (line 3), but it can also end without a 'return'.` | An action that returns a value must end with a `return` on every way through it. Add one at the very end, or an `else` branch that returns. |
| `I do not know a command called 'wait'.` | The line starts with a word that is not a command. The hint suggests a similar one (`Did you mean 'say'?`) or lists the commands. |
| `'If' should be written with small letters.` | Keywords are written in small letters: `if`, `then`, `say`. |
| `I do not know a command or helper called 'read' ...` | A word in the middle of a line is not known. Check the spelling; values are joined with `+`. |
| `I expected 'to' here ...` (in a `for` line) | A counting loop is `for i from 1 to 10 do`, optionally with `step`. |
| `A text cannot be changed letter by letter.` | `set t at 0 to "x"` works for lists only. Build a new text with `part` and `+`. |
| `I don't know a module called 'x'.` | `import x` found no module and no file `x.plain` next to the program. The hint lists both. |
| `The file 'x' is already imported.` / `... the imports go in a circle.` | Import every file once; two files cannot import each other. |
| `A file that is imported can only contain 'import', 'define', 'action' and 'let ... fixed'.` | Move lines that *do* something into the main program. |
| `'x' is already defined in the file lib.plain, line 3.` | A name can be used once only, across all imported files. |
| `'pi' is fixed, so it cannot be changed.` | The name was made with `let pi be ... fixed`. Take `fixed` away if it has to change. This also covers `add`, `remove`, `sort` and changing a field through a fixed name. |
| `'x' is already a fixed value of the program.` / `The parameter 'x' has the name of a fixed value.` | A top-level fixed value is known everywhere, so no variable or parameter may have its name. |
| `I don't know a variable called 'name'.` (in an action, for a fixed value) | Only fixed values made of plain numbers, text and `true`/`false` are known inside actions. Pass others in as a parameter. |
| `'fail' needs a text as its message ...` | Write `fail "Something went wrong"`. |

When an error happens inside an action, a note tells you which action and with which argument types it was compiled.
An action that is never called is checked too; the note then says so.
A mistake in an imported file is shown with the name of that file and its line.

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
| `That position does not exist in this text ...` | `text at 9` is past the last letter; the first letter is at position 0. |
| `The step of a 'for' loop cannot be 0.` | `for i from 1 to 10 step 0` would never end. |
| *your own message* | Made by `fail "..."` in the program. Catch it with `try`. |
| `'replace' needs a text to look for, but it is empty.` | `replace(text, "", ...)` has nothing to replace. |
| `The computer ran out of memory.` | Allocation failed. |

Catch runtime errors with `try ... catch error then ... end`; the message is available as text in the variable you name.
