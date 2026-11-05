"""Parser: turns tokens into a syntax tree (recursive descent)."""

import copy
import difflib
import os

from . import modules as M
from . import nodes as N
from . import typesys as T
from .errors import PlainError
from .lexer import KEYWORDS, describe, tokenize

BLOCK_END = ("end", "else", "catch")
COMPARE_OPS = ("=", "<", ">", "<=", ">=")

def word(tok, name):
    """A contextual keyword: an ordinary name that has a special meaning only in certain places."""
    return tok.kind in ("NAME", "KEYWORD") and tok.value == name


class Parser:
    def __init__(self, tokens, base_dir=None, shared=None, chain=()):
        self.toks = tokens
        self.i = 0
        self.no_at = 0  # > 0 while 'at' must not be read as a list index (draw text ... at x, y)
        self.modules = []   # the modules this file imported (their sentences can be used here)
        self.all_modules = []   # those, and the modules that the imported files need
        self.base_dir = base_dir            # where 'import name' looks for name.plain
        self.shared = shared if shared is not None else {"done": set()}     # files already brought in
        self.chain = chain                  # the files that are being read right now (to find circles)
        self.local = []                     # (name, path) of the own files this file imported
        self.imported = []                  # definitions that came from imported own files

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
            if tok.kind == "NAME" and tok.value.lower() == word:
                hint = f"Keywords are written with small letters: {word}"
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
            before = self.toks[self.i - 1] if self.i else None
            hint = "Every statement goes on its own line."
            if before is not None and before.kind == "NAME" and tok.kind in ("NAME", "TEXT", "NUMBER"):
                hint = (f"I do not know a command or helper called '{before.value}' that goes with {describe(tok)}. "
                        "Check the spelling. Values are joined with +, and every statement goes on its own line.")
            if tok.kind == "NAME" and tok.value.lower() in KEYWORDS:
                hint = f"Keywords are written with small letters: {tok.value.lower()}"
            self.error(tok, f"I did not expect {describe(tok)} here.", hint)

    # ---- program and blocks ------------------------------------------------

    def parse_program(self):
        body = []
        self.skip_newlines()
        while self.cur.is_kw("import"):
            self.parse_import()
            self.skip_newlines()
        while self.cur.kind != "EOF":
            body.append(self.parse_statement(top_level=True))
            self.skip_newlines()
        types = [node for module in self.all_modules for node in module.struct_nodes()]
        return N.Program(types + self.imported + body, [m.name for m in self.all_modules])

    def parse_import(self):
        start = self.advance()
        name = self.expect_name("a module name")
        module = M.load(name.value)
        if module is None:
            self.import_file(name)
        else:
            if module in self.modules:
                self.error(name, f"The module '{name.value}' is already imported.")
            self.modules.append(module)
            if module not in self.all_modules:
                self.all_modules.append(module)
        self.end_statement()
        return start

    def import_file(self, name):
        """import lib: bring in the actions and types of lib.plain, which lies next to this program."""
        known = ", ".join(M.available()) or "none"
        if not self.base_dir:
            self.error(name, f"I don't know a module called '{name.value}'.",
                       f"The modules are: {known}. To import your own file, save this program first: "
                       f"the file '{name.value}.plain' is looked for next to it.")
        path = os.path.abspath(os.path.join(self.base_dir, name.value + ".plain"))
        key = os.path.normcase(path)
        if not os.path.isfile(path):
            mine = sorted(f[:-6] for f in os.listdir(self.base_dir) if f.endswith(".plain"))
            more = f" Your own files next to this program: {', '.join(mine[:8])}{', ...' if len(mine) > 8 else ''}." \
                if mine else ""
            self.error(name, f"I don't know a module called '{name.value}'.",
                       f"The modules are: {known}. There is no file '{name.value}.plain' next to this program.{more}")
        if key in self.chain:
            self.error(name, f"'{name.value}' imports this file again, so the imports go in a circle.",
                       "Move what both files need into a third file that imports nothing.")
        if any(k == key for _n, k in self.local):
            self.error(name, f"The file '{name.value}' is already imported.")
        self.local.append((name.value, key))
        if key in self.shared["done"]:
            return              # another file has brought it in already
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            self.error(name, f"I cannot read '{name.value}.plain': {exc.strerror}.")
        try:
            sub = Parser(tokenize(text), os.path.dirname(path), self.shared, self.chain + (key,))
            program = sub.parse_program()
        except PlainError as err:
            if err.file is None:
                err.file = path
            raise
        self.shared["done"].add(key)
        module_types = {n.name for m in sub.all_modules for n in m.struct_nodes()}
        for node in program.body:
            if isinstance(node, N.DefineStruct) and node.line == 0 and node.name in module_types:
                continue        # a type of a module: it is added once for the whole program
            if not isinstance(node, (N.DefineStruct, N.ActionDef)) and not (isinstance(node, N.Let) and node.fixed):
                raise PlainError("A file that is imported can only contain 'import', 'define', 'action' "
                                 "and 'let ... fixed'.", node.line, node.col,
                                 "Lines that do something belong in the main program.", file=path)
            if node.file is None:
                node.file = path
            self.imported.append(node)
        for module in sub.all_modules:
            if module not in self.all_modules:
                self.all_modules.append(module)

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
                "try": self.parse_try, "sort": self.parse_sort, "run": self.parse_run,
                "fail": self.parse_fail,
            }.get(tok.value)
            if tok.value == "import":
                self.error(tok, "'import' must be at the top of the program, before everything else.",
                           "For example:  import window")
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
            if tok.value == "do":
                hint = "To run an action write: run name(values). 'do' only ends the head of a while, for each or action."
            self.error(tok, f"I did not expect {describe(tok)} here.", hint)
        if tok.kind == "NAME":
            if tok.value.lower() in KEYWORDS and tok.value != tok.value.lower():
                self.error(tok, f"'{tok.value}' should be written with small letters.",
                           f"Keywords are written with small letters: {tok.value.lower()}")
            sentence = self.parse_module_command()
            if sentence is not None:
                return sentence
            if tok.value == "wait" and (self.peek().kind in ("NUMBER", "NAME", "TEXT") or self.peek().is_sym("-")):
                return self.parse_wait()
            return self.parse_expr_statement()
        self.error(tok, f"I did not expect {describe(tok)} at the start of a line.")

    # ---- sentences from modules (open window ..., draw circle at ..., window is open) -----

    def head_matches(self, pattern):
        return all(word(self.peek(k), w) for k, w in enumerate(pattern.head_words()))

    def parse_module_command(self):
        candidates = [p for m in self.modules for p in m.commands() if self.head_matches(p)]
        if candidates:
            pattern = max(candidates, key=lambda p: p.head)
            tok = self.cur
            args = self.parse_pattern(pattern)
            self.end_statement()
            return N.ExprStmt(N.Call(pattern.func, args, None, pattern.module, line=tok.line, col=tok.col),
                              line=tok.line, col=tok.col)
        for module in M.load_all():
            if module in self.modules:
                continue
            for pattern in module.commands():
                if self.head_matches(pattern):
                    self.import_hint(module, " ".join(pattern.head_words()))
        return None

    def import_hint(self, module, sentence):
        self.error(self.cur, f"'{sentence}' belongs to the module '{module.name}', which is not imported.",
                   f"Add this line at the very top of your program:  import {module.name}")

    def try_question(self):
        """A sentence that gives a value, e.g. 'window is open'. Returns None when the words are something else."""
        tok = self.cur
        if tok.kind != "NAME":
            return None
        for module in M.load_all():
            for pattern in module.questions():
                if not word(tok, pattern.parts[0].word):
                    continue
                saved, saved_at = self.i, self.no_at
                try:
                    args = self.parse_pattern(pattern)
                except PlainError:
                    self.i, self.no_at = saved, saved_at
                    continue
                if module not in self.modules:
                    self.i = saved
                    self.import_hint(module, pattern.example())
                return N.Call(pattern.func, args, None, pattern.module, line=tok.line, col=tok.col)
        return None

    def parse_pattern(self, pattern):
        """Read one sentence of a module: its words and commas must be there, its values are expressions."""
        hint = "Write: " + pattern.example()
        args = []
        for k, part in enumerate(pattern.parts):
            if part.kind == "word":
                if not word(self.cur, part.word):
                    self.error(self.cur, f"I expected '{part.word}' here but found {describe(self.cur)}.", hint)
                self.advance()
            elif part.kind == "comma":
                self.expect_sym(",", hint)
            elif part.type == "color":
                args += self.parse_color(pattern.module, hint)
            else:
                following = pattern.parts[k + 1] if k + 1 < len(pattern.parts) else None
                guard = following is not None and following.kind == "word" and following.word == "at"
                self.no_at += guard
                try:
                    args.append(self.parse_additive())
                finally:
                    self.no_at -= guard
        return args

    def parse_color(self, module_name, hint):
        """A color name (orange), a Color value (sky) or three numbers: returns red, green, blue expressions."""
        tok = self.cur
        colors = M.load(module_name).colors
        if tok.kind == "NAME" and tok.value in colors and self.peek().kind in ("NEWLINE", "EOF"):
            self.advance()
            return [N.Num(float(v), line=tok.line, col=tok.col) for v in colors[tok.value]]
        value = self.parse_additive()
        if self.cur.is_sym(","):            # use color 255, 128, 0
            self.advance()
            green = self.parse_additive()
            self.expect_sym(",", "Write three numbers from 0 to 255:  use color 255, 128, 0")
            return [value, green, self.parse_additive()]
        return [N.Field(part, copy.deepcopy(value), line=tok.line, col=tok.col)
                for part in ("red", "green", "blue")]

    def parse_expr_statement(self):
        start = self.cur
        if self.peek().is_sym("="):
            self.error(self.peek(), "'=' only compares values in Plain.",
                       f"To change a variable write: set {start.value} to ...")
        following = self.peek()
        if start.kind == "NAME" and following.kind in ("NAME", "TEXT", "NUMBER") and not following.is_kw("of", "at"):
            known = sorted((KEYWORDS | {"wait"}) - {"be", "to", "then", "do", "end", "else", "in", "as", "of", "at", "from", "times",
                                       "each", "catch", "and", "or", "not", "mod", "true", "false", "nothing", "list"})
            close = difflib.get_close_matches(start.value, known, n=1)
            hint = (f"Did you mean '{close[0]}'?" if close else
                    "The commands are: " + ", ".join(known) + ".")
            self.error(start, f"I do not know a command called '{start.value}'.", hint)
        expr = self.parse_expr()
        if isinstance(expr, N.Call) and start.kind == "NAME" and start.value == expr.name:
            self.error(start, f"To run the action '{start.value}' start the line with 'run'.",
                       f"Write: run {start.value}(...)")
        if not isinstance(expr, N.Call):
            self.error(start, "This line does nothing on its own.",
                       "Use 'say' to show a value, 'let' to create a variable or 'set' to change one.")
        self.end_statement()
        return N.ExprStmt(expr, line=start.line, col=start.col)

    def parse_run(self):
        """run name(values): runs an action. 'run' always means: run the code of an action."""
        start = self.advance()
        hint = "Write: run name(value1, value2)"
        if self.cur.kind != "NAME" or not self.peek().is_sym("("):
            self.error(self.cur, f"I expected the name of an action after 'run' but found {describe(self.cur)}.", hint)
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
        fixed = False
        if word(self.cur, "fixed"):             # let pi be 3.14159 fixed
            self.advance()
            fixed = True
        self.end_statement()
        return N.Let(name.value, value, fixed, line=start.line, col=start.col)

    def parse_fail(self):
        """fail "message": stop with an error of your own."""
        start = self.advance()
        if self.cur.kind in ("NEWLINE", "EOF"):
            self.error(self.cur, "'fail' needs a message.", 'Write: fail "Something went wrong"')
        value = self.parse_expr()
        self.end_statement()
        return N.Fail(value, line=start.line, col=start.col)

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
        if self.cur.kind == "NAME" and self.peek().is_kw("from"):
            return self.parse_for_count(start)
        if not self.cur.is_kw("each"):
            self.error(self.cur, f"I expected 'each' or a name here but found {describe(self.cur)}.",
                       "Write: for each item in items do    or    for i from 1 to 10 do")
        self.expect_kw("each", "Write: for each item in items do")
        var = self.expect_name("a variable name")
        self.expect_kw("in", "Write: for each item in items do")
        iterable = self.parse_expr()
        self.expect_kw("do", "Write: for each item in items do")
        body = self.parse_block(("end",), start, "'for each'")
        self.expect_kw("end")
        self.end_statement()
        return N.ForEach(var.value, iterable, body, line=start.line, col=start.col)

    def parse_for_count(self, start):
        """for i from 1 to 10 do ... end     (optional: step 2, or step -1 to count down)"""
        hint = "Write: for i from 1 to 10 do    or    for i from 10 to 1 step -1 do"
        var = self.advance()
        self.expect_kw("from", hint)
        first = self.parse_expr()
        self.expect_kw("to", hint)
        last = self.parse_expr()
        step = None
        if word(self.cur, "step"):
            self.advance()
            step = self.parse_expr()
        self.expect_kw("do", hint)
        body = self.parse_block(("end",), start, "'for'")
        self.expect_kw("end")
        self.end_statement()
        return N.ForCount(var.value, first, last, step, body, line=start.line, col=start.col)

    def parse_wait(self):
        """wait 2 seconds     (also: wait 1 second, wait pause)"""
        start = self.advance()
        seconds = self.parse_additive()
        if word(self.cur, "second") or word(self.cur, "seconds"):
            self.advance()
        self.end_statement()
        return N.Wait(seconds, line=start.line, col=start.col)

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
            self.error(self.cur, "An action lists the values it needs after 'takes'.", hint)
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
        question = self.try_question()
        if question is not None:
            return question
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


def parse(tokens, base_dir=None):
    """base_dir: the folder of the program; 'import name' looks there for name.plain."""
    return Parser(tokens, base_dir).parse_program()
