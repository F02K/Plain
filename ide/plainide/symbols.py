"""Understands a Plain program well enough to explain a name when you click on it.

It works on the text (no full parse), so it also works while the program still has mistakes in it.
`analyze(source, line, column)` returns where the name is created and where it is used.
"""

import bisect
import re

TOKEN = re.compile(r'(?P<comment>\bnote:[^\n]*)|(?P<string>"(?:[^"\\\n]|\\.)*"?)|'
                   r'(?P<number>\b\d+(?:\.\d+)?\b)|(?P<word>[A-Za-z_][A-Za-z0-9_]*)')
OPENERS = ("if", "while", "repeat", "for", "try", "action", "define")

HELP = {
    "let": "let name be value  creates a new variable.",
    "set": "set name to value  gives an existing variable a new value.",
    "say": "say value  shows a value in the output.",
    "input": "input \"question\"  asks the user for text. input number \"question\"  asks for a number.",
    "if": "if condition then ... end  runs the lines only when the condition is true.",
    "then": "then  ends the condition of an if.",
    "else": "else  runs when the condition above was false. else if checks another condition.",
    "end": "end  closes the block that was opened by if, while, repeat, for, action, define or try.",
    "repeat": "repeat 5 times ... end  runs the lines a fixed number of times.",
    "times": "times  belongs to repeat.",
    "while": "while condition do ... end  repeats the lines as long as the condition is true.",
    "do": "do  ends the head of a while, for each or action.",
    "run": "run name(values)  runs an action.",
    "for": "for each item in items do ... end  runs the lines for every item of a list (or letter of a text).  "
           "for i from 1 to 10 do ... end  counts; add step 2 or step -1 to count differently.",
    "each": "each  belongs to for each.",
    "in": "in  names the list that for each walks through.",
    "stop": "stop  leaves the loop right now.",
    "skip": "skip  jumps to the next round of the loop.",
    "action": "action name takes(a, b) do ... end  creates a reusable piece of code. Run it with run name(1, 2).",
    "takes": "takes(a, b)  lists the values an action needs.",
    "return": "return value  gives a value back to the caller and leaves the action.",
    "define": "define Name as ... end  creates your own type with fields.",
    "as": "as  gives a field its type, for example x as number.",
    "list": "list of number  is a list that holds numbers.",
    "of": "x of player  reads the field x of a thing. length of text  uses a helper.",
    "at": "list at 0  is the item at a position (the first is 0). In draw commands it gives the position.",
    "add": "add value to list  puts a value at the end of a list.",
    "remove": "remove value from list, or remove at 0 from list.",
    "from": "from  belongs to remove, to draw line and to for i from 1 to 10.",
    "sort": "sort list  puts the items in order.",
    "try": "try ... catch error then ... end  runs the lines and handles a run-time error.",
    "catch": "catch error then  runs when something inside try went wrong; error holds the message.",
    "and": "and  is true when both sides are true.",
    "or": "or  is true when at least one side is true.",
    "not": "not  turns true into false and false into true.",
    "mod": "a mod b  is the remainder of a divided by b.",
    "true": "true  is a boolean value.", "false": "false  is a boolean value.",
    "nothing": "nothing  means: no value.",
    "random": "random(1, 6)  gives a random whole number from 1 to 6.",
    "min": "min(a, b)  is the smaller number.", "max": "max(a, b)  is the bigger number.",
    "part": "part(text, start, count)  cuts a piece out of a text (the first letter is 0).",
    "contains": "contains(text, piece)  is true when piece is inside text. Also works for lists.",
    "length": "length of text  is the number of letters.",
    "upper": "upper of text  makes the letters big.", "lower": "lower of text  makes the letters small.",
    "round": "round of 2.5  rounds to a whole number.", "abs": "abs of -3  removes the minus sign.",
    "sqrt": "sqrt of 9  is the square root.",
    "import": "import window  adds the sentences of a module (here: windows and drawing). It goes at the top of the program.",
    "open": "open window \"Title\" with width 640 and height 480  opens the program window.",
    "close": "close window  closes the program window.",
    "show": "show window  shows everything that was drawn and waits for the next frame.",
    "clear": "clear window with color black  paints the whole window.",
    "window": "window is open  is true until the player closes the window. Also: open window, show window, clear window.",
    "draw": "draw circle at x, y radius r  /  draw rectangle at x, y size w by h  /  draw line from ... to ...  /  draw text ... at x, y",
    "use": "use color orange  sets the color for everything that is drawn next.",
    "color": "Colors: red green blue yellow orange purple pink brown gray white black, or Color(red: 0, green: 0, blue: 0).",
    "key": "key \"left\" is pressed  is true while that key is held down.",
    "pressed": "key \"left\" is pressed  is true while that key is held down.",
    "mouse": "mouse x, mouse y  tell where the mouse is. mouse is down  is true while the left button is held.",
    "Color": "Color(red: 0, green: 0, blue: 0)  is a color made of red, green and blue (0 to 255).",
    "number": "number  is the type for numbers.", "text": "text  is the type for words and sentences.",
    "boolean": "boolean  is the type for true and false.",
}


def _line_starts(source):
    starts = [0]
    for m in re.finditer("\n", source):
        starts.append(m.end())
    return starts


def scan(source):
    """All names in the code (not in comments or texts): (word, start, end, line)."""
    starts = _line_starts(source)
    out = []
    for m in TOKEN.finditer(source):
        if m.lastgroup == "word":
            out.append((m.group(), m.start(), m.end(), bisect.bisect_right(starts, m.start())))
    return out


def blocks(source):
    """Top level action and define blocks: (kind, name, first line, last line, params, fields)."""
    lines = source.split("\n")
    result, depth, current = [], 0, None
    for number, raw in enumerate(lines, 1):
        code = re.sub(r"\bnote:.*$", "", raw).strip()
        first = re.match(r"[A-Za-z_]+", code)
        first = first.group() if first else ""
        if depth == 0 and first in ("action", "define"):
            m = re.match(r"(?:action|define)\s+([A-Za-z_][A-Za-z0-9_]*)", code)
            params = []
            tm = re.search(r"\btakes\s*\(([^)]*)\)", code)
            if tm:
                params = [p.strip() for p in tm.group(1).split(",") if p.strip()]
            current = {"kind": first, "name": m.group(1) if m else "", "first": number,
                       "last": len(lines), "params": params, "fields": {}}
        elif current and current["kind"] == "define" and depth == 1 and first and first != "end":
            fm = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+as\s+(.*)$", code)
            if fm:
                current["fields"][fm.group(1)] = fm.group(2).strip()
        if first in OPENERS and not (first == "if" and raw.strip().startswith("else")):
            depth += 1
        elif first == "end":
            depth = max(0, depth - 1)
            if depth == 0 and current:
                current["last"] = number
                result.append(current)
                current = None
    if current:
        result.append(current)
    return result


def analyze(source, line, column):
    """Explain the name at (line, column), both 1-based... column 0-based. Returns a dict or None."""
    starts = _line_starts(source)
    if not 1 <= line <= len(starts):
        return None
    offset = starts[line - 1] + column
    words = scan(source)
    index = next((i for i, w in enumerate(words) if w[1] <= offset <= w[2]), None)
    if index is None:
        return None
    word = words[index][0]
    block_list = blocks(source)
    actions = [b for b in block_list if b["kind"] == "action"]

    def action_at(ln):
        return next((a for a in actions if a["first"] <= ln <= a["last"]), None)

    def previous(i, n=1):
        return words[i - n][0] if i - n >= 0 else ""

    # Which tokens create a name?  (declaration kind or None)
    def declaration(i):
        w, _s, _e, ln = words[i]
        prev = previous(i)
        if prev == "let":
            return "variable"
        if prev == "each" and previous(i, 2) == "for":
            return "loop"
        if prev == "for" and i + 1 < len(words) and words[i + 1][0] == "from":
            return "loop"           # for i from 1 to 10 do
        if prev == "catch":
            return "error"
        if prev == "action":
            return "action"
        if prev == "define":
            return "type"
        block = next((b for b in block_list if b["first"] <= ln <= b["last"]), None)
        if block and block["kind"] == "action" and ln == block["first"] and w in block["params"] and prev != "action":
            return "parameter"
        if block and block["kind"] == "define" and ln > block["first"] and w in block["fields"] \
                and i + 1 < len(words) and words[i + 1][0] == "as" and words[i + 1][3] == ln:
            return "field"
        return None

    decls = [declaration(i) for i in range(len(words))]

    # Names that belong to one action only (its parameters and its own variables).
    local = {}
    for i, kind in enumerate(decls):
        if kind in ("variable", "loop", "error", "parameter"):
            a = action_at(words[i][3])
            if a:
                local.setdefault(a["first"], set()).add(words[i][0])

    here = action_at(words[index][3])
    scoped = here if here and word in local.get(here["first"], ()) else None

    def in_scope(i):
        ln = words[i][3]
        a = action_at(ln)
        if scoped:
            return a is scoped
        return not (a and words[i][0] in local.get(a["first"], ()))

    marks = [i for i, w in enumerate(words) if w[0] == word and in_scope(i)]
    defs = [i for i in marks if decls[i]]
    uses = [i for i in marks if not decls[i]]
    result = {"word": word, "defs": [(words[i][1], words[i][2]) for i in defs],
              "uses": [(words[i][1], words[i][2]) for i in uses], "kind": None, "text": ""}

    if not defs:
        if word in HELP:
            result["kind"] = "help"
            result["text"] = HELP[word]
            result["defs"], result["uses"] = [], []
        else:
            result["kind"] = "unknown"
            result["text"] = f"'{word}' is not created anywhere in this scope yet. " \
                             f"Create it with: let {word} be ..." if marks else ""
        return result

    first = defs[0]
    kind = decls[first]
    ln = words[first][3]
    times = len(uses)
    writes = sum(1 for i in uses if previous(i) == "set")
    used = f"used {times} time{'s' if times != 1 else ''}"
    if kind == "action":
        block = next(b for b in actions if b["first"] == ln)
        params = ", ".join(block["params"]) or "no values"
        text = f"action {word} takes({params}) - line {ln} - called {times} time{'s' if times != 1 else ''}"
    elif kind == "type":
        block = next(b for b in block_list if b["first"] == ln)
        text = f"type {word} with the fields {', '.join(block['fields']) or 'none'} - line {ln} - {used}"
    elif kind == "field":
        block = next(b for b in block_list if b["first"] <= ln <= b["last"])
        text = f"field of {block['name']} ({block['fields'][word]}) - line {ln} - {used}"
    elif kind == "parameter":
        text = f"value given to the action {here['name'] if here else ''} - {used}"
    elif kind == "loop":
        text = f"takes every item of the list in turn (line {ln}) - {used}"
    elif kind == "error":
        text = f"the error message (line {ln}) - {used}"
    else:
        text = f"variable - created in line {ln} - changed {writes} time{'s' if writes != 1 else ''} - {used}"
    result["kind"] = kind
    result["text"] = text
    return result
