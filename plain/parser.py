"""Parser: turns tokens into a syntax tree (recursive descent)."""

import copy

from . import nodes as N
from . import typesys as T
from .errors import PlainError
from .lexer import describe

BLOCK_END = ("end", "else", "catch")
COMPARE_OPS = ("=", "<", ">", "<=", ">=")

# Named colors for 'use color orange' (red, green, blue).
COLORS = {
    "red": (230, 50, 50), "green": (50, 180, 70), "blue": (50, 100, 230),
    "yellow": (250, 220, 50), "orange": (255, 150, 30), "purple": (150, 70, 200),
    "pink": (255, 130, 180), "brown": (140, 90, 50), "gray": (128, 128, 128),
    "white": (255, 255, 255), "black": (0, 0, 0),
}

# The window helpers used to be written as functions. They are sentences now.
REMOVED_CALLS = {
    "window": 'Write: open window "My game" with width 640 and height 480',
    "color": "Write: use color orange   (or: use color mycolor)",
    "clear": "Write: clear window   or   clear window with color black",
    "rectangle": "Write: draw rectangle at 10, 10 size 100 by 50",
    "circle": "Write: draw circle at 200, 150 radius 30",
    "line": "Write: draw line from 0, 0 to 100, 100",
    "write": 'Write: draw text "Score" at 10, 10',
    "show": "Write: show window",
    "close_window": "Write: close window",
    "running": "Write: while window is open do",
    "pressed": 'Write: if key "left" is pressed then',
    "mouse_x": "Write: mouse x",
    "mouse_y": "Write: mouse y",
    "mouse_down": "Write: mouse is down",
}


def word(tok, name):
    """A contextual keyword: an ordinary name that has a special meaning only in certain places."""
    return tok.kind == "NAME" and tok.value == name


class Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0
        self.no_at = 0  # > 0 while 'at' must not be read as a list index (draw text ... at x, y)

    # ---- token helpers -----------------------------------------------------

    @property
    def cur(self):
        return self.toks[self.i]

    def peek(self, k=1):
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def advance(self):
        tok = self.toks[self.i]
        if tok.kind != "EOF":
            self.i += 1
        return tok

    def skip_newlines(self):
        while self.cur.kind == "NEWLINE":
            self.advance()

    def error(self, tok, message, hint=None):
        raise PlainError(message, tok.line, tok.col, hint)

    def expect_kw(self, word, hint=None):
        tok = self.cur
        if not tok.is_kw(word):
            self.error(tok, f"I expected '{word}' here but found {describe(tok)}.", hint)
        return self.advance()

    def expect_sym(self, sym, hint=None):
        tok = self.cur
        if not tok.is_sym(sym):
            self.error(tok, f"I expected '{sym}' here but found {describe(tok)}.", hint)
        return self.advance()

    def expect_name(self, what):
        tok = self.cur
        if tok.kind == "KEYWORD":
            self.error(tok, f"'{tok.value}' is a reserved word, so it cannot be used as {what}.",
                       "Pick another name.")
        if tok.kind != "NAME":
            self.error(tok, f"I expected {what} here but found {describe(tok)}.")
        return self.advance()

    def end_statement(self):
        tok = self.cur
        if tok.kind == "NEWLINE":
            self.advance()
        elif tok.kind == "EOF" or tok.is_kw(*BLOCK_END):
            pass
        else:
            self.error(tok, f"I did not expect {describe(tok)} here.",
                       "Every statement goes on its own line.")

    # ---- program and blocks ------------------------------------------------

    def parse_program(self):
        body = []
        self.skip_newlines()
        while self.cur.kind != "EOF":
            body.append(self.parse_statement(top_level=True))
            self.skip_newlines()
        uses_color = any(word(t, "Color") for t in self.toks)
        if uses_color and not any(isinstance(b, N.DefineStruct) and b.name == "Color" for b in body):
            body.insert(0, N.DefineStruct("Color", [("red", "number", 0), ("green", "number", 0),
                                                    ("blue", "number", 0)], line=0, col=0))
        return N.Program(body)

    def parse_block(self, stops, opener, what):
        body = []
        while True:
            self.skip_newlines()
            tok = self.cur
            if tok.is_kw(*stops):
                return body
            if tok.kind == "EOF":
                self.error(opener, f"This {what} is never closed.", "Add 'end' after its last line.")
            body.append(self.parse_statement())

    # ---- statements --------------------------------------------------------

    def parse_statement(self, top_level=False):
        tok = self.cur
        if tok.kind == "KEYWORD":
            handler = {
                "let": self.parse_let, "set": self.parse_set, "say": self.parse_say,
                "if": self.parse_if, "repeat": self.parse_repeat, "while": self.parse_while,
                "for": self.parse_for, "stop": self.parse_stop, "skip": self.parse_skip,
                "return": self.parse_return, "add": self.parse_add, "remove": self.parse_remove,
                "try": self.parse_try, "sort": self.parse_sort, "do": self.parse_do,
            }.get(tok.value)
            if tok.value in ("action", "define"):
                if not top_level:
                    self.error(tok, f"'{tok.value}' can only be used at the top level of the program, "
                                    "not inside another block.")
                return self.parse_action() if tok.value == "action" else self.parse_define()
            if handler:
                return handler()
            hint = None
            if tok.value == "end":
                hint = "There is an 'end' without a matching if/while/repeat/for/action/define/try."
            self.error(tok, f"I did not expect {describe(tok)} here.", hint)
        if tok.kind == "NAME":
            window_statement = self.parse_window_statement()
            if window_statement is not None:
                return window_statement
            return self.parse_expr_statement()
        self.error(tok, f"I did not expect {describe(tok)} at the start of a line.")

    # ---- windows and drawing (sentences instead of function calls) ---------

    def gfx(self, name, args, tok):
        return N.Call(name, args, None, line=tok.line, col=tok.col)

    def gfx_stmt(self, name, args, tok):
        return N.ExprStmt(self.gfx(name, args, tok), line=tok.line, col=tok.col)

    def expect_word(self, name, hint):
        tok = self.cur
        if not word(tok, name):
            self.error(tok, f"I expected '{name}' here but found {describe(tok)}.", hint)
        return self.advance()

    def parse_color(self):
        """A color name (orange) or a Color value (sky): returns red, green, blue expressions."""
        tok = self.cur
        if tok.kind == "NAME" and tok.value in COLORS and self.peek().kind in ("NEWLINE", "EOF"):
            self.advance()
            return [N.Num(float(v), line=tok.line, col=tok.col) for v in COLORS[tok.value]]
        value = self.parse_additive()
        if self.cur.is_sym(","):            # use color 255, 128, 0
            self.advance()
            green = self.parse_additive()
            self.expect_sym(",", "Write: use color 255, 128, 0   (red, green, blue from 0 to 255)")
            return [value, green, self.parse_additive()]
        return [N.Field(part, copy.deepcopy(value), line=tok.line, col=tok.col)
                for part in ("red", "green", "blue")]

    def parse_window_statement(self):
        tok, nxt = self.cur, self.peek()
        w = tok.value
        if w == "open" and word(nxt, "window"):
            hint = 'Write: open window "My game" with width 640 and height 480'
            self.advance()
            self.advance()
            title = self.parse_additive()
            self.expect_word("with", hint)
            self.expect_word("width", hint)
            width = self.parse_additive()
            self.expect_kw("and", hint)
            self.expect_word("height", hint)
            height = self.parse_additive()
            self.end_statement()
            return self.gfx_stmt("window", [title, width, height], tok)
        if w in ("close", "show") and word(nxt, "window"):
            self.advance()
            self.advance()
            self.end_statement()
            return self.gfx_stmt("close_window" if w == "close" else "show", [], tok)
        if w == "clear" and word(nxt, "window"):
            self.advance()
            self.advance()
            if word(self.cur, "with"):
                self.advance()
                self.expect_word("color", "Write: clear window with color black")
                rgb = self.parse_color()
                self.end_statement()
                return N.Group([self.gfx_stmt("color", rgb, tok), self.gfx_stmt("clear", [], tok)],
                               line=tok.line, col=tok.col)
            self.end_statement()
            return self.gfx_stmt("clear", [], tok)
        if w == "use" and word(nxt, "color"):
            self.advance()
            self.advance()
            rgb = self.parse_color()
            self.end_statement()
            return self.gfx_stmt("color", rgb, tok)
        if w == "draw" and nxt.kind == "NAME" and nxt.value in ("rectangle", "circle", "line", "text"):
            self.advance()
            shape = self.advance().value
            if shape == "rectangle":
                hint = "Write: draw rectangle at 10, 10 size 100 by 50"
                self.expect_kw("at", hint)
                x = self.parse_additive()
                self.expect_sym(",", hint)
                y = self.parse_additive()
                self.expect_word("size", hint)
                width = self.parse_additive()
                self.expect_word("by", hint)
                height = self.parse_additive()
                args = [x, y, width, height]
            elif shape == "circle":
                hint = "Write: draw circle at 200, 150 radius 30"
                self.expect_kw("at", hint)
                x = self.parse_additive()
                self.expect_sym(",", hint)
                y = self.parse_additive()
                self.expect_word("radius", hint)
                args = [x, y, self.parse_additive()]
            elif shape == "line":
                hint = "Write: draw line from 0, 0 to 100, 100"
                self.expect_kw("from", hint)
                x1 = self.parse_additive()
                self.expect_sym(",", hint)
                y1 = self.parse_additive()
                self.expect_kw("to", hint)
                x2 = self.parse_additive()
                self.expect_sym(",", hint)
                args = [x1, y1, x2, self.parse_additive()]
            else:
                hint = 'Write: draw text "Score" at 10, 10'
                self.no_at += 1
                text = self.parse_additive()
                self.no_at -= 1
                self.expect_kw("at", hint)
                x = self.parse_additive()
                self.expect_sym(",", hint)
                args = [text, x, self.parse_additive()]
            self.end_statement()
            return self.gfx_stmt({"text": "write"}.get(shape, shape), args, tok)
        return None

    def parse_expr_statement(self):
        start = self.cur
        if self.peek().is_sym("="):
            self.error(self.peek(), "'=' only compares values in Plain.",
                       f"To change a variable write: set {start.value} to ...")
        expr = self.parse_expr()
        if isinstance(expr, N.Call) and start.kind == "NAME" and start.value == expr.name:
            self.error(start, f"To run the action '{start.value}' start the line with 'do'.",
                       f"Write: do {start.value}(...)")
        if not isinstance(expr, N.Call):
            self.error(start, "This line does nothing on its own.",
                       "Use 'say' to show a value, 'let' to create a variable or 'set' to change one.")
        self.end_statement()
        return N.ExprStmt(expr, line=start.line, col=start.col)

    def parse_do(self):
        """do name(values): runs an action. 'do' always means: run the code of an action."""
        start = self.advance()
        hint = "Write: do name(value1, value2)"
        if self.cur.kind != "NAME" or not self.peek().is_sym("("):
            self.error(self.cur, f"I expected the name of an action after 'do' but found {describe(self.cur)}.", hint)
        call = self.parse_primary()
        self.end_statement()
        return N.ExprStmt(call, line=start.line, col=start.col)

    def parse_let(self):
        start = self.advance()
        name = self.expect_name("a variable name")
        if self.cur.is_sym("="):
            self.error(self.cur, "Use 'be' to create a variable.", f"Write: let {name.value} be ...")
        self.expect_kw("be", f"Write: let {name.value} be <value>")
        if self.cur.is_kw("list"):
            ltok = self.advance()
            self.expect_kw("of", "Write: let items be list of number")
            value = N.ListInit(self.parse_type(), line=ltok.line, col=ltok.col)
        else:
            value = self.parse_expr()
        self.end_statement()
        return N.Let(name.value, value, line=start.line, col=start.col)

    def parse_set(self):
        start = self.advance()
        target = self.parse_access()
        if not isinstance(target, (N.Var, N.Field, N.Index)):
            self.error(start, "I can only change a variable, a field (x of player) or a list item (list at 0).")
        if self.cur.is_sym("="):
            self.error(self.cur, "Use 'to' to give a variable a new value.", "Write: set x to 5")
        self.expect_kw("to", "Write: set <name> to <value>")
        value = self.parse_expr()
        self.end_statement()
        return N.Set(target, value, line=start.line, col=start.col)

    def parse_say(self):
        start = self.advance()
        value = self.parse_expr()
        self.end_statement()
        return N.Say(value, line=start.line, col=start.col)

    def parse_if(self):
        start = self.advance()
        branches = []
        else_body = None
        cond = self.parse_expr()
        self.expect_kw("then", "An if needs 'then' after its condition.")
        body = self.parse_block(("else", "end"), start, "'if'")
        branches.append((cond, body))
        while self.cur.is_kw("else"):
            self.advance()
            if self.cur.is_kw("if"):
                self.advance()
                cond = self.parse_expr()
                self.expect_kw("then", "An 'else if' needs 'then' after its condition.")
                body = self.parse_block(("else", "end"), start, "'if'")
                branches.append((cond, body))
            else:
                else_body = self.parse_block(("end",), start, "'if'")
                break
        self.expect_kw("end")
        self.end_statement()
        return N.If(branches, else_body, line=start.line, col=start.col)

    def parse_repeat(self):
        start = self.advance()
        count = self.parse_expr()
        self.expect_kw("times", "Write: repeat 5 times")
        body = self.parse_block(("end",), start, "'repeat'")
        self.expect_kw("end")
        self.end_statement()
        return N.Repeat(count, body, line=start.line, col=start.col)

    def parse_while(self):
        start = self.advance()
        cond = self.parse_expr()
        self.expect_kw("do", "Write: while <condition> do")
        body = self.parse_block(("end",), start, "'while'")
        self.expect_kw("end")
        self.end_statement()
        return N.While(cond, body, line=start.line, col=start.col)

    def parse_for(self):
        start = self.advance()
        self.expect_kw("each", "Write: for each item in items do")
        var = self.expect_name("a variable name")
        self.expect_kw("in", "Write: for each item in items do")
        iterable = self.parse_expr()
        self.expect_kw("do", "Write: for each item in items do")
        body = self.parse_block(("end",), start, "'for each'")
        self.expect_kw("end")
        self.end_statement()
        return N.ForEach(var.value, iterable, body, line=start.line, col=start.col)

    def parse_stop(self):
        start = self.advance()
        self.end_statement()
        return N.Stop(line=start.line, col=start.col)

    def parse_skip(self):
        start = self.advance()
        self.end_statement()
        return N.Skip(line=start.line, col=start.col)

    def parse_return(self):
        start = self.advance()
        value = None
        if self.cur.kind != "NEWLINE" and self.cur.kind != "EOF" and not self.cur.is_kw(*BLOCK_END):
            value = self.parse_expr()
        self.end_statement()
        return N.Return(value, line=start.line, col=start.col)

    def parse_add(self):
        start = self.advance()
        item = self.parse_expr()
        self.expect_kw("to", "Write: add <value> to <list>")
        target = self.parse_expr()
        self.end_statement()
        return N.Add(item, target, line=start.line, col=start.col)

    def parse_sort(self):
        start = self.advance()
        target = self.parse_expr()
        self.end_statement()
        return N.Sort(target, line=start.line, col=start.col)

    def parse_remove(self):
        start = self.advance()
        if self.cur.is_kw("at"):
            self.advance()
            index = self.parse_expr()
            self.expect_kw("from", "Write: remove at <position> from <list>")
            target = self.parse_expr()
            self.end_statement()
            return N.RemoveAt(index, target, line=start.line, col=start.col)
        item = self.parse_expr()
        self.expect_kw("from", "Write: remove <value> from <list>")
        target = self.parse_expr()
        self.end_statement()
        return N.Remove(item, target, line=start.line, col=start.col)

    def parse_try(self):
        start = self.advance()
        self.end_statement()
        body = self.parse_block(("catch",), start, "'try'")
        self.expect_kw("catch")
        name = self.expect_name("a name for the error message")
        self.expect_kw("then", "Write: catch error then")
        handler = self.parse_block(("end",), start, "'try'")
        self.expect_kw("end")
        self.end_statement()
        return N.Try(body, name.value, handler, line=start.line, col=start.col)

    def parse_action(self):
        start = self.advance()
        name = self.expect_name("an action name")
        hint = "Write: action name takes(parameter1, parameter2) do"
        params = []
        if self.cur.is_sym("("):
            self.error(self.cur, "Actions list their values with 'takes' now.", hint)
        if word(self.cur, "takes"):
            self.advance()
            self.expect_sym("(", hint)
            if not self.cur.is_sym(")"):
                while True:
                    params.append(self.expect_name("a parameter name").value)
                    if self.cur.is_sym(","):
                        self.advance()
                        continue
                    break
            self.expect_sym(")", hint)
        self.expect_kw("do", "Write: action name takes(parameter) do   or, without values:   action name do")
        body = self.parse_block(("end",), start, "'action'")
        self.expect_kw("end")
        self.end_statement()
        return N.ActionDef(name.value, params, body, line=start.line, col=start.col)

    def parse_define(self):
        start = self.advance()
        name = self.expect_name("a name for the new type")
        self.expect_kw("as", "Write: define Player as")
        self.end_statement()
        fields = []
        while True:
            self.skip_newlines()
            if self.cur.is_kw("end"):
                break
            if self.cur.kind == "EOF":
                self.error(start, "This 'define' is never closed.", "Add 'end' after the last field.")
            fname = self.expect_name("a field name")
            self.expect_kw("as", "Write: <field> as number")
            ftype = self.parse_type()
            self.end_statement()
            fields.append((fname.value, ftype, fname.line))
        self.expect_kw("end")
        self.end_statement()
        return N.DefineStruct(name.value, fields, line=start.line, col=start.col)

    def parse_type(self):
        tok = self.cur
        if tok.is_kw("list"):
            self.advance()
            self.expect_kw("of", "Write: list of number")
            return T.list_of(self.parse_type())
        name = self.expect_name("a type name")
        if name.value in T.PRIMITIVES:
            return name.value
        return T.struct(name.value)

    # ---- expressions -------------------------------------------------------

    def parse_expr(self):
        left = self.parse_not()
        used = None
        while self.cur.is_kw("and", "or"):
            op_tok = self.advance()
            if used and used != op_tok.value:
                self.error(op_tok, "'and' and 'or' are mixed here.",
                           "Use parentheses to show what you mean, e.g. (a and b) or c")
            used = op_tok.value
            right = self.parse_not()
            left = N.Binary(op_tok.value, left, right, line=op_tok.line, col=op_tok.col)
        return left

    def parse_not(self):
        if self.cur.is_kw("not"):
            tok = self.advance()
            return N.Unary("not", self.parse_not(), line=tok.line, col=tok.col)
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_additive()
        if self.cur.is_sym(*COMPARE_OPS):
            op = self.advance()
            right = self.parse_additive()
            if self.cur.is_sym(*COMPARE_OPS):
                self.error(self.cur, "Two comparisons in a row do not work.",
                           "Split them with 'and', e.g. a < b and b < c")
            return N.Binary(op.value, left, right, line=op.line, col=op.col)
        return left

    def parse_additive(self):
        left = self.parse_term()
        while self.cur.is_sym("+", "-"):
            op = self.advance()
            right = self.parse_term()
            left = N.Binary(op.value, left, right, line=op.line, col=op.col)
        return left

    def parse_term(self):
        left = self.parse_unary()
        while self.cur.is_sym("*", "/") or self.cur.is_kw("mod"):
            op = self.advance()
            right = self.parse_unary()
            left = N.Binary(op.value, left, right, line=op.line, col=op.col)
        return left

    def parse_unary(self):
        tok = self.cur
        if tok.is_sym("-"):
            self.advance()
            return N.Unary("-", self.parse_unary(), line=tok.line, col=tok.col)
        if tok.is_kw("input"):
            self.advance()
            as_number = False
            nxt = self.peek()
            if self.cur.kind == "NAME" and self.cur.value == "number" and \
                    (nxt.kind in ("TEXT", "NAME") or nxt.is_sym("(")):
                self.advance()
                as_number = True
            return N.Input(self.parse_additive(), as_number, line=tok.line, col=tok.col)
        return self.parse_access()

    def parse_access(self):
        tok = self.cur
        if tok.kind == "NAME" and self.peek().is_kw("of"):
            self.advance()
            self.advance()
            if self.cur.is_sym("-"):
                minus = self.advance()
                obj = N.Unary("-", self.parse_access(), line=minus.line, col=minus.col)
            else:
                obj = self.parse_access()
            return N.Field(tok.value, obj, line=tok.line, col=tok.col)
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while self.cur.is_kw("at") and not self.no_at:
            tok = self.advance()
            index = self.parse_primary()
            expr = N.Index(expr, index, line=tok.line, col=tok.col)
        return expr

    def parse_primary(self):
        tok = self.cur
        if tok.kind == "NUMBER":
            self.advance()
            return N.Num(tok.value, line=tok.line, col=tok.col)
        if tok.kind == "TEXT":
            self.advance()
            return N.Str(tok.value, line=tok.line, col=tok.col)
        if tok.is_kw("true", "false"):
            self.advance()
            return N.Bool(tok.value == "true", line=tok.line, col=tok.col)
        if tok.is_kw("nothing"):
            self.advance()
            return N.Nothing(line=tok.line, col=tok.col)
        if word(tok, "window") and word(self.peek(), "is") and word(self.peek(2), "open"):
            self.advance()
            self.advance()
            self.advance()
            return self.gfx("running", [], tok)
        if word(tok, "mouse"):
            nxt = self.peek()
            if word(nxt, "x") or word(nxt, "y"):
                self.advance()
                self.advance()
                return self.gfx("mouse_" + nxt.value, [], tok)
            if word(nxt, "is") and word(self.peek(2), "down"):
                self.advance()
                self.advance()
                self.advance()
                return self.gfx("mouse_down", [], tok)
        if word(tok, "key") and self.peek().kind in ("TEXT", "NAME") and word(self.peek(2), "is") \
                and word(self.peek(3), "pressed"):
            self.advance()
            arg = self.advance()
            self.advance()
            self.advance()
            key = N.Str(arg.value, line=arg.line, col=arg.col) if arg.kind == "TEXT" \
                else N.Var(arg.value, line=arg.line, col=arg.col)
            return self.gfx("pressed", [key], tok)
        if tok.kind == "NAME":
            self.advance()
            if tok.value == "ask" and self.cur.kind == "TEXT":
                self.error(tok, "'ask' is now called 'input'.", 'Write: let name be input "Your name?"')
            if self.cur.is_sym("("):
                return self.parse_call(tok)
            return N.Var(tok.value, line=tok.line, col=tok.col)
        if tok.is_sym("("):
            self.advance()
            saved, self.no_at = self.no_at, 0
            expr = self.parse_expr()
            self.no_at = saved
            self.expect_sym(")", "A '(' was opened but never closed.")
            return expr
        if tok.kind == "KEYWORD":
            self.error(tok, f"I expected a value here but found the word {describe(tok)}.")
        self.error(tok, f"I expected a value here but found {describe(tok)}.")

    def parse_call(self, name_tok):
        if name_tok.value in REMOVED_CALLS:
            self.error(name_tok, f"'{name_tok.value}(...)' is not used any more.", REMOVED_CALLS[name_tok.value])
        self.expect_sym("(")
        args, named = [], None
        if not self.cur.is_sym(")"):
            while True:
                if self.cur.kind == "NAME" and self.peek().is_sym(":"):
                    if named is None:
                        if args:
                            self.error(self.cur, "Do not mix plain values and 'name: value' pairs.")
                        named = []
                    fname = self.advance()
                    self.advance()
                    named.append((fname.value, self.parse_expr()))
                else:
                    if named is not None:
                        self.error(self.cur, "Do not mix plain values and 'name: value' pairs.")
                    args.append(self.parse_expr())
                if self.cur.is_sym(","):
                    self.advance()
                    continue
                break
        self.expect_sym(")", "A '(' was opened but never closed.")
        return N.Call(name_tok.value, args, named, line=name_tok.line, col=name_tok.col)


def parse(tokens):
    return Parser(tokens).parse_program()
