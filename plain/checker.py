"""Checker: finds mistakes in a program before it runs, and explains them in plain words.

Plain has no type annotations, so the checker works out the types itself. An action is checked once
for each combination of argument types it is called with (like a template). Nothing is decided at run
time, so a program that passes the checker cannot mix up numbers, text and lists.
"""

import copy
import dataclasses
import difflib
import os
import re

from . import library as L
from . import modules as M
from . import nodes as N
from . import typesys as T
from .errors import PlainError


class FnCtx:
    """What the checker knows about the code it is looking at right now."""

    def __init__(self, inst=None, file=None):
        self.inst = inst
        self.file = file            # the imported file the code comes from (None: the program itself)
        self.scopes = [{}]
        self.loops = 0
        self.is_main = inst is None
        self.fixed = set()          # the names in here that were made with 'fixed' (they cannot be changed)


class Instance:
    def __init__(self):
        self.ret = None         # None while still being checked
        self.ret_line = None


class PyInfo:
    """An action or question that a module gets from Python (a line of a 'from python' block)."""

    def __init__(self, node, ns, receiver, recv_type, params):
        self.node = node
        self.ns = ns                    # the name of the namespace that holds the module's Python code
        self.receiver = receiver        # the name after 'of', or None
        self.recv_type = recv_type
        self.params = params
        self.gives = node.gives if node.gives is not None else T.NOTHING


class Checker:
    def __init__(self, program):
        self.program = program
        self.structs = {}
        self.actions = {}
        self.pyactions = {}         # name -> PyInfo: what the modules get from Python
        self.exports = {}           # (file, short name) -> (type name, node): the types that Python builds
        program.pyfiles = {}        # namespace -> path of the Python file, for the Python writer
        self.instances = {}
        self.fn = None
        self.cur_file = None        # the file of the definition that is being looked at
        self.globals = {}           # name -> type of the fixed values that every action can read
        self.main_only = set()      # top-level fixed names that actions cannot read (their value is not plain)
        program.constants = []      # their 'let ... fixed' lines, in order (the Python writer needs them)

    # ---- small helpers -------------------------------------------------------

    def error(self, node, message, hint=None):
        file = (self.fn.file if self.fn else None) or getattr(node, "file", None) or self.cur_file
        raise PlainError(message, getattr(node, "line", None) or None,
                         getattr(node, "col", None) or None, hint, file=file)

    def check_type(self, t, node):
        if T.is_list(t):
            self.check_type(t[1], node)
        elif T.is_struct(t) and t[1] not in self.structs:
            close = difflib.get_close_matches(t[1], list(self.structs), n=1)
            self.error(node, f"I don't know a type called '{t[1]}'.", f"Did you mean '{close[0]}'?" if close else None)
        return t

    # ---- scopes --------------------------------------------------------------

    def declare(self, name, t, node):
        if name in self.globals:
            self.error(node, f"'{name}' is already a fixed value of the program.",
                       "Pick another name for the variable.")
        for scope in self.fn.scopes:
            if name in scope:
                self.error(node, f"There is already a variable called '{name}'.",
                           f"To change it use: set {name} to ...")
        self.fn.scopes[-1][name] = t

    def lookup(self, name, node):
        for scope in reversed(self.fn.scopes):
            if name in scope:
                return scope[name]
        if name in self.globals:
            return self.globals[name]
        known = [n for sc in self.fn.scopes for n in sc]
        close = difflib.get_close_matches(name, known, n=1)
        self.not_imported(name, node)
        if not self.fn.is_main and name in self.main_only:
            hint = (f"'{name}' is fixed, but actions only know fixed values made of plain numbers, text and "
                    "true/false (or calculated from those). Pass it in as a parameter.")
        elif close:
            hint = f"Did you mean '{close[0]}'?"
        elif not self.fn.is_main:
            hint = "An action only knows its own parameters and variables. Pass other values in as parameters."
        else:
            hint = f"Create it first with: let {name} be ..."
        self.error(node, f"I don't know a variable called '{name}'.", hint)

    def not_imported(self, name, node):
        """A name that a module offers, used without 'import': say which line is missing."""
        module = M.provided_names().get(name)
        if module:
            self.error(node, f"'{name}' belongs to the module '{module}', which is not imported.",
                       f"Add this line at the very top of your program:  import {module}")

    # ---- program -------------------------------------------------------------

    def check(self):
        self.collect_definitions()
        self.fn = FnCtx()
        for stmt in self.program.body:
            if not isinstance(stmt, (N.DefineStruct, N.ActionDef, N.PythonExport, N.PythonBlock)):
                self.statement(stmt)
        self.check_unused_actions()

    def check_unused_actions(self):
        """An action that is never called still gets checked, with values of unknown type, so that
        a mistake in it (a wrong name, a missing 'return') is found now and not when it is used later."""
        used = {name for name, _types in self.instances}
        for name, action in self.actions.items():
            if name not in used:
                self.instance(action, (T.ANY,) * len(action.params))

    def collect_definitions(self):
        for stmt in self.program.body:
            if isinstance(stmt, N.DefineStruct):
                if stmt.name in self.structs or stmt.name in T.PRIMITIVES or stmt.name == "nothing" \
                        or stmt.name in L.CALLS:
                    self.error(stmt, f"The type '{stmt.name}' is defined twice or is a built-in name.",
                               self.first_definition(stmt.name))
                self.structs[stmt.name] = stmt
        for stmt in self.program.body:
            if isinstance(stmt, N.PythonExport):
                self.collect_export(stmt)
        for stmt in self.program.body:
            if isinstance(stmt, N.PythonBlock):
                self.collect_block(stmt)
        self.cur_file = None
        for sd in self.structs.values():
            if sd.readonly and sd.py is None:
                self.cur_file = sd.file
                self.error(sd, f"The type '{sd.name}' has read-only fields, so Python has to build it.",
                           "Only a type that a module gives to Python (export ...) can have 'readonly' fields.")
        self.cur_file = None
        for stmt in self.program.body:
            if isinstance(stmt, N.ActionDef):
                if stmt.name in self.pyactions:
                    self.error(stmt, f"The name '{stmt.name}' is already used by an action of a module.")
                if stmt.name in L.CALLS:
                    self.error(stmt, f"'{stmt.name}' is a built-in helper, so it cannot be used as an action name.",
                               "Pick another name.")
                if stmt.name in self.actions or stmt.name in self.structs:
                    self.error(stmt, f"The name '{stmt.name}' is already used by an action or a type.",
                               self.first_definition(stmt.name))
                if len(set(stmt.params)) != len(stmt.params):
                    self.error(stmt, "Two parameters have the same name.")
                self.actions[stmt.name] = stmt
        for name, sd in list(self.structs.items()):
            fields = {}
            self.cur_file = sd.file
            if not sd.fields:
                self.error(sd, f"The type '{name}' has no fields.")
            for fname, ftype, fline in sd.fields:
                if fname in fields:
                    self.error(N.Node(line=fline), f"The field '{fname}' appears twice in '{name}'.")
                self.check_type(ftype, N.Node(line=fline))
                fields[fname] = ftype
            sd.layout = fields
        self.cur_file = None
        self.collect_constants()

    def python_file(self, node, pyfile):
        """The path of a module's Python file and the name of the namespace that holds its code."""
        base = os.path.dirname(node.file) if node.file else ""
        path = os.path.join(base, pyfile if pyfile.endswith(".py") else pyfile + ".py")
        stem = lambda text: re.sub(r"\W", "_", os.path.splitext(os.path.basename(text))[0])
        ns = f"_m_{stem(node.file or 'main')}_{stem(pyfile)}"
        self.program.pyfiles[ns] = path
        return path, ns

    def collect_export(self, stmt):
        self.cur_file = stmt.file
        if not stmt.file:
            self.error(stmt, "'export' can only be used in the .plain file of a module.")
        sd = self.structs.get(stmt.type_name)
        if sd is None or sd.file != stmt.file:
            self.error(stmt, f"I don't know a type called '{stmt.type_name}' in this file.",
                       f"Define it above this line:  define {stmt.type_name} as ... end")
        key = (stmt.file, stmt.alias)
        if key in self.exports:
            self.error(stmt, f"The name '{stmt.alias}' is used twice in export lines.")
        path, ns = self.python_file(stmt, stmt.pyfile)
        api = M.python_api(path)
        if api is None:
            self.error(stmt, f"I cannot read the Python file '{stmt.pyfile}' (next to {os.path.basename(stmt.file)}).")
        if api.get(stmt.type_name, (None,))[0] != "class":
            self.error(stmt, f"The Python file '{stmt.pyfile}' has no class called '{stmt.type_name}'.",
                       f"Python builds the type, so it needs:  class {stmt.type_name}:")
        sd.py = ns
        self.exports[key] = (stmt.type_name, stmt)

    def collect_block(self, stmt):
        self.cur_file = stmt.file
        if not stmt.file:
            self.error(stmt, "'from python' can only be used in the .plain file of a module.")
        path, ns = self.python_file(stmt, stmt.pyfile)
        api = M.python_api(path)
        if api is None:
            self.error(stmt, f"I cannot read the Python file '{stmt.pyfile}' (next to {os.path.basename(stmt.file)}).")
        for a in stmt.actions:
            if a.name in L.CALLS or a.name in self.structs or a.name in self.pyactions:
                self.error(a, f"The name '{a.name}' is a built-in helper, a type or already an action of a module.",
                           self.first_definition(a.name))
            recv_type = None
            if a.receiver:
                key = (stmt.file, a.receiver)
                if key not in self.exports:
                    self.error(a, f"'{a.receiver}' is not a thing that this file gives to Python.",
                               f'Write this first:  export Type as {a.receiver} to python "{stmt.pyfile}"')
                recv_type = T.struct(self.exports[key][0])
            for param in a.params:
                self.check_type(param.type, a)
            known = api.get(a.name)
            if known is None or known[0] != "function":
                self.error(a, f"The Python file '{stmt.pyfile}' has no function called '{a.name}'.",
                           f"It needs:  def {a.name}(...)")
            given = (1 if a.receiver else 0) + len(a.params) + 1        # the thing, the values, the line number
            _kind, fewest, most = known
            if not fewest <= given <= most:
                self.error(a, f"In {stmt.pyfile} the function '{a.name}' takes {fewest if fewest == most else f'{fewest} to {most}'} "
                              f"value(s), but Plain gives it {given}: " +
                              ", ".join(([a.receiver] if a.receiver else []) + [p.name for p in a.params] + ["the line number"]) + ".")
            self.pyactions[a.name] = PyInfo(a, ns, a.receiver, recv_type, a.params)

    def collect_constants(self):
        """Top-level 'let ... fixed' lines with a plain value (numbers, text, true/false, other fixed values and
        calculations with them) are known everywhere, also inside actions. They are made before the program starts."""
        self.fn = FnCtx()
        for stmt in self.program.body:
            if isinstance(stmt, N.Let) and stmt.fixed and self.is_constant(stmt.value):
                self.cur_file = stmt.file
                if stmt.name in self.globals:
                    self.error(stmt, f"There is already a fixed value called '{stmt.name}'.")
                self.globals[stmt.name] = self.expr(stmt.value)
                self.program.constants.append(stmt)
            elif isinstance(stmt, N.Let) and stmt.fixed:
                self.main_only.add(stmt.name)
        self.fn, self.cur_file = None, None
        for action in self.actions.values():
            for p in action.params:
                if p in self.globals:
                    self.cur_file = action.file
                    self.error(action, f"The parameter '{p}' has the name of a fixed value.",
                               "Pick another name for the parameter.")

    def is_constant(self, node):
        if isinstance(node, (N.Num, N.Str, N.Bool)):
            return True
        if isinstance(node, N.Unary):
            return self.is_constant(node.operand)
        if isinstance(node, N.Binary):
            return self.is_constant(node.left) and self.is_constant(node.right)
        if isinstance(node, N.Var):
            return node.name in self.globals
        if isinstance(node, N.Call) and node.name in self.structs and not node.args and node.named is not None:
            return all(self.is_constant(value) for _name, value in node.named)      # Color(red: 1, green: 2, blue: 3)
        return False

    def is_fixed(self, name):
        for scope in self.fn.scopes:
            if name in scope:
                return name in self.fn.fixed
        return name in self.globals

    def check_changeable(self, target):
        """Nothing that was made with 'fixed' may be changed: not set, and no adding to or sorting of a fixed list."""
        node = target
        while isinstance(node, (N.Field, N.Index)):
            node = node.obj
        if isinstance(node, N.Var) and self.is_fixed(node.name):
            self.error(node, f"'{node.name}' is fixed, so it cannot be changed.",
                       f"If it has to change, take 'fixed' away from the line that creates '{node.name}'.")

    def first_definition(self, name):
        """Where a name was defined first, for the hint of an error about a name that is used twice."""
        node = self.structs.get(name) or self.actions.get(name)
        if node is None:
            return None
        where = f"the file {os.path.basename(node.file)}" if node.file else "this program"
        return f"'{name}' is already defined in {where}, line {node.line}. Every name can be used only once."

    # ---- statements ----------------------------------------------------------

    def block(self, body):
        self.fn.scopes.append({})
        for stmt in body:
            self.statement(stmt)
        self.fn.scopes.pop()

    def statement(self, stmt):
        getattr(self, "s_" + type(stmt).__name__)(stmt)

    def s_Let(self, s):
        if s in self.program.constants:         # a fixed value of the whole program: known already
            return
        if isinstance(s.value, N.ListInit):
            t = T.list_of(self.check_type(s.value.element_type, s.value))
        else:
            t = self.expr(s.value)
            if t == T.NOTHING:
                self.error(s.value, "This gives no value, so it cannot be stored in a variable.")
        self.declare(s.name, t, s)
        if s.fixed:
            self.fn.fixed.add(s.name)

    def s_Set(self, s):
        target = s.target
        self.check_changeable(target)
        if isinstance(target, N.Var):
            vt = self.lookup(target.name, target)
            self.expect_type(vt, self.expr(s.value), s.value, f"the variable '{target.name}'")
        elif isinstance(target, N.Field):
            ot = self.expr(target.obj)
            ft = self.field_type(ot, target)
            if T.is_struct(ot) and target.name in self.structs[ot[1]].readonly:
                self.error(target, f"'{target.name}' of a {ot[1]} can only be read, not changed.",
                           "Python keeps this value up to date, so there is nothing to set.")
            self.expect_type(ft, self.expr(s.value), s.value, f"the field '{target.name}'")
        else:
            lt = self.expr(target.obj)
            if lt == T.TEXT:
                self.error(target, "A text cannot be changed letter by letter.",
                           "Build a new text instead, for example: set t to part(t, 0, 2) + \"x\"")
            item = self.list_type(lt, target, "at")
            self.expect_number(self.expr(target.index), target.index, "A list position")
            self.expect_type(item, self.expr(s.value), s.value, "this list item")

    def s_Say(self, s):
        t = self.expr(s.value)
        if t not in (T.TEXT, T.NUMBER, T.BOOLEAN, T.NOTHING, T.ANY):
            if T.is_list(t) and t[1] == T.TEXT:
                hint = 'Join the items into one text: say join(items, ", ")'
            elif T.is_list(t):
                hint = "Walk through the list and say every item: for each item in items do say item end"
            else:
                hint = "Say its fields one by one, for example: say health of player"
            self.error(s.value, f"'say' cannot show {self.describe(t)} directly.", hint)

    def s_If(self, s):
        for cond, body in s.branches:
            self.condition(cond, "An if")
            self.block(body)
        if s.else_body is not None:
            self.block(s.else_body)

    def s_Repeat(self, s):
        self.expect_number(self.expr(s.count), s.count, "'repeat' needs a number, but this")
        self.loop_body(s.body)

    def s_While(self, s):
        self.condition(s.cond, "A while")
        self.loop_body(s.body)

    def s_ForEach(self, s):
        t = self.expr(s.iterable)
        if t == T.TEXT:
            item = T.TEXT                   # the letters of a text
        elif t == T.ANY or T.is_list(t):
            item = self.list_type(t, s.iterable, "for each")
        else:
            self.error(s.iterable, f"'for each' needs a list or a text, but this is {self.describe(t)}.")
        self.fn.scopes.append({})
        self.declare(s.var, item, s)
        self.loop_body(s.body)
        self.fn.scopes.pop()

    def s_ForCount(self, s):
        self.expect_number(self.expr(s.start), s.start, "The start of a 'for' loop")
        self.expect_number(self.expr(s.stop), s.stop, "The end of a 'for' loop")
        if s.step is not None:
            self.expect_number(self.expr(s.step), s.step, "The step of a 'for' loop")
        self.fn.scopes.append({})
        self.declare(s.var, T.NUMBER, s)
        self.loop_body(s.body)
        self.fn.scopes.pop()

    def loop_body(self, body):
        self.fn.loops += 1
        self.block(body)
        self.fn.loops -= 1

    def s_Stop(self, s):
        if not self.fn.loops:
            self.error(s, "'stop' can only be used inside a loop.")

    def s_Skip(self, s):
        if not self.fn.loops:
            self.error(s, "'skip' can only be used inside a loop.")

    def s_Return(self, s):
        if self.fn.is_main:
            self.error(s, "'return' can only be used inside an action.")
        inst = self.fn.inst
        t = T.NOTHING if s.value is None else self.expr(s.value)
        if inst.ret is None or inst.ret == T.ANY:
            inst.ret = t
            inst.ret_line = s.line
        elif not self.same(inst.ret, t):
            self.error(s, f"This action already returns {self.describe(inst.ret)} (line {inst.ret_line}), "
                          f"but here it returns {self.describe(t)}.",
                       "An action must always return the same kind of value.")

    def s_Wait(self, s):
        self.expect_number(self.expr(s.seconds), s.seconds, "The time to wait")

    def s_Fail(self, s):
        t = self.expr(s.value)
        if t not in (T.TEXT, T.ANY):
            self.error(s.value, f"'fail' needs a text as its message, but this is {self.describe(t)}.",
                       'For example: fail "Something went wrong"')

    def s_ExprStmt(self, s):
        self.call(s.expr, want_value=False)

    def s_Add(self, s):
        self.check_changeable(s.target)
        item = self.list_type(self.expr(s.target), s.target, "add")
        self.expect_type(item, self.expr(s.item), s.item, "this list")

    def s_Remove(self, s):
        self.check_changeable(s.target)
        item = self.list_type(self.expr(s.target), s.target, "remove")
        self.expect_type(item, self.expr(s.item), s.item, "this list")

    def s_RemoveAt(self, s):
        self.check_changeable(s.target)
        self.list_type(self.expr(s.target), s.target, "remove at")
        self.expect_number(self.expr(s.index), s.index, "A list position")

    def s_Sort(self, s):
        self.check_changeable(s.target)
        lt = self.expr(s.target)
        if lt != T.ANY and (not T.is_list(lt) or lt[1] not in (T.NUMBER, T.TEXT)):
            self.error(s.target, f"'sort' needs a list of numbers or text, but this is {self.describe(lt)}.")

    def s_Try(self, s):
        self.block(s.body)
        self.fn.scopes.append({})
        self.declare(s.error_name, T.TEXT, s)
        self.block(s.handler)
        self.fn.scopes.pop()

    # ---- type helpers --------------------------------------------------------

    def same(self, want, got):
        return want == got or T.ANY in (want, got)

    def list_type(self, t, node, what):
        """The type of the items of a list (any, when the list itself is not known)."""
        if t == T.ANY:
            return T.ANY
        if not T.is_list(t):
            self.error(node, f"'{what}' needs a list, but this is {self.describe(t)}.")
        return t[1]

    def describe(self, t):
        if t == T.ANY:
            return "a value"
        if t == T.NOTHING:
            return "nothing"
        if t in T.PRIMITIVES:
            return f"a {t}"
        if T.is_list(t):
            return f"a {T.type_name(t)}"
        return f"a '{t[1]}'"

    def expect_type(self, want, got, node, what):
        if not self.same(want, got):
            self.error(node, f"{what.capitalize()} holds {self.describe(want)}, but this value is {self.describe(got)}.")

    def expect_number(self, t, node, what):
        if t not in (T.NUMBER, T.ANY):
            self.error(node, f"{what} must be a number, but this is {self.describe(t)}.")

    def condition(self, node, what):
        t = self.expr(node)
        if t not in (T.BOOLEAN, T.ANY):
            self.error(node, f"{what} condition must be true or false, but this is {self.describe(t)}.",
                       "Compare values with =, <, >, <= or >=")

    def field_type(self, obj_type, node):
        if obj_type == T.ANY:
            return T.ANY
        if not T.is_struct(obj_type):
            self.error(node, f"'{node.name} of ...' needs a thing with fields, but this is {self.describe(obj_type)}.")
        layout = self.structs[obj_type[1]].layout
        if node.name not in layout:
            self.error(node, f"'{obj_type[1]}' has no field called '{node.name}'.",
                       "Its fields are: " + ", ".join(layout))
        return layout[node.name]

    # ---- expressions ---------------------------------------------------------

    def expr(self, node):
        return getattr(self, "x_" + type(node).__name__)(node)

    def x_Num(self, e):
        return T.NUMBER

    def x_Str(self, e):
        return T.TEXT

    def x_Bool(self, e):
        return T.BOOLEAN

    def x_Nothing(self, e):
        return T.NOTHING

    def x_Var(self, e):
        return self.lookup(e.name, e)

    def x_ListInit(self, e):
        self.error(e, "'list of ...' can only be used directly after 'let ... be'.")

    def x_Unary(self, e):
        t = self.expr(e.operand)
        if e.op == "-":
            self.expect_number(t, e.operand, "The value after '-'")
            return T.NUMBER
        if t not in (T.BOOLEAN, T.ANY):
            self.error(e.operand, f"'not' needs true or false, but this is {self.describe(t)}.")
        return T.BOOLEAN

    def x_Input(self, e):
        t = self.expr(e.prompt)
        if t not in (T.TEXT, T.ANY):
            self.error(e.prompt, f"'input' needs a text, but this is {self.describe(t)}.")
        return T.NUMBER if e.as_number else T.TEXT

    def x_Field(self, e):
        ot = self.expr(e.obj)
        if ot == T.ANY:
            return L.OF[e.name][1] if e.name in L.OF else T.NUMBER if e.name == "size" else T.ANY
        if T.is_list(ot) and e.name == "size":
            return T.NUMBER
        if e.name in L.OF and not T.is_struct(ot):
            want, result = L.OF[e.name]
            wanted = want if isinstance(want, list) else [want]
            if ot not in wanted:
                self.error(e, f"'{e.name} of ...' needs {' or '.join(self.describe(w) for w in wanted)}, "
                              f"but this is {self.describe(ot)}.")
            return result
        return self.field_type(ot, e)

    def x_Index(self, e):
        lt = self.expr(e.obj)
        if lt == T.TEXT:                    # one letter of a text
            self.expect_number(self.expr(e.index), e.index, "A position in a text")
            return T.TEXT
        item = self.list_type(lt, e, "at")
        self.expect_number(self.expr(e.index), e.index, "A list position")
        return item

    def x_Binary(self, e):
        op = e.op
        if op in ("and", "or"):
            for side in (e.left, e.right):
                t = self.expr(side)
                if t not in (T.BOOLEAN, T.ANY):
                    self.error(side, f"'{op}' needs true or false on both sides, but this is {self.describe(t)}.",
                               "For example: health > 0 and health < 100")
            return T.BOOLEAN
        lt, rt = self.expr(e.left), self.expr(e.right)
        if op == "+" and (lt == T.TEXT or rt == T.TEXT):
            for t, side in ((lt, e.left), (rt, e.right)):
                if t not in (T.TEXT, T.NUMBER, T.BOOLEAN, T.ANY):
                    self.error(side, f"I cannot join text with {self.describe(t)}.")
            return T.TEXT
        if op == "=":
            if not self.same(lt, rt):
                self.error(e, f"I cannot compare {self.describe(lt)} with {self.describe(rt)}.")
            return T.BOOLEAN
        if T.ANY in (lt, rt):               # an action that is never called: the other side must still fit
            for t, side in ((lt, e.left), (rt, e.right)):
                if t not in (T.NUMBER, T.ANY) and not (op == "+" and t == T.TEXT):
                    self.error(e, f"'{op}' needs two numbers, but I got {self.describe(lt)} and {self.describe(rt)}.")
            return T.BOOLEAN if op in ("<", ">", "<=", ">=") else T.ANY if op == "+" else T.NUMBER
        if lt != T.NUMBER or rt != T.NUMBER:
            hint = "'+' adds numbers or joins text." if op == "+" else None
            self.error(e, f"'{op}' needs two numbers, but I got {self.describe(lt)} and {self.describe(rt)}.", hint)
        return T.BOOLEAN if op in ("<", ">", "<=", ">=") else T.NUMBER

    def x_Call(self, e):
        return self.call(e, want_value=True)

    # ---- calls ---------------------------------------------------------------

    def call(self, e, want_value):
        if e.name in L.CALLS:
            if not want_value and L.CALLS[e.name][1] != T.NOTHING:
                self.error(e, f"'{e.name}' gives a value, so this line does nothing on its own.",
                           "Use it inside 'say' or 'let', for example: say " + L.EXAMPLES[e.name])
            return self.builtin_call(e)
        if e.name in self.structs:
            return self.construct(e)
        if e.name in self.pyactions:
            return self.py_call(e, want_value)
        if e.name not in self.actions:
            self.not_imported(e.name, e)
            close = difflib.get_close_matches(e.name, list(self.actions) + list(self.pyactions) + list(self.structs), n=1)
            hint = f"Did you mean '{close[0]}'?" if close else \
                f"Define it first with: action {e.name} takes(...) do ... end"
            self.error(e, f"I don't know an action or type called '{e.name}'.", hint)
        action = self.actions[e.name]
        e.bound = self.bind_arguments(e, action.params)
        types = []
        for arg in e.bound:
            t = self.expr(arg)
            if t == T.NOTHING:
                self.error(arg, "This gives no value, so it cannot be passed to an action.")
            types.append(t)
        inst = self.instance(action, tuple(types))
        if inst.ret is None:
            if want_value:
                self.error(e, f"I don't know yet what '{e.name}' gives back, because it calls itself "
                              "before its first 'return'.",
                           "Put a 'return' with a value (the base case) before the recursive call.")
            return T.NOTHING
        return inst.ret

    def bind_arguments(self, e, names, default_for=None):
        """The values of a call in the order of the parameters: plain values first, then 'name: value' pairs;
        default_for(index, values) gives the value of a parameter that was left out (or None)."""
        named = e.named or []
        if len(e.args) > len(names):
            self.error(e, f"'{e.name}' needs {len(names)} value(s) ({', '.join(names) or 'none'}) "
                          f"but you gave {len(e.args)}.")
        slots = list(e.args) + [None] * (len(names) - len(e.args))
        for fname, fexpr in named:
            if fname not in names:
                self.error(fexpr, f"'{e.name}' has no value called '{fname}'.", "Its values are: " + ", ".join(names))
            i = names.index(fname)
            if slots[i] is not None:
                self.error(fexpr, f"The value '{fname}' is given twice.")
            slots[i] = fexpr
        missing = []
        for i, name in enumerate(names):
            if slots[i] is None and default_for is not None:
                slots[i] = default_for(i, slots)
            if slots[i] is None:
                missing.append(name)
        if missing:
            if not named and default_for is None:
                self.error(e, f"'{e.name}' needs {len(names)} value(s) ({', '.join(names) or 'none'}) "
                              f"but you gave {len(e.args)}.")
            self.error(e, f"'{e.name}' needs a value for: {', '.join(missing)}.")
        return slots

    def substitute(self, node, name, replacement):
        """A copy of an expression in which the variable 'name' is replaced by another expression."""
        if isinstance(node, N.Var) and node.name == name:
            return copy.deepcopy(replacement)
        if isinstance(node, N.Node):
            clone = copy.copy(node)
            for f in dataclasses.fields(node):
                setattr(clone, f.name, self.substitute(getattr(node, f.name), name, replacement))
            return clone
        if isinstance(node, list):
            return [self.substitute(item, name, replacement) for item in node]
        if isinstance(node, tuple):
            return tuple(self.substitute(item, name, replacement) for item in node)
        return node

    def py_call(self, e, want_value):
        info = self.pyactions[e.name]
        names = ([info.receiver] if info.receiver else []) + [p.name for p in info.params]
        wants = ([info.recv_type] if info.receiver else []) + [p.type for p in info.params]
        offset = 1 if info.receiver else 0

        def default_for(i, slots):
            if i < offset or (info.receiver and slots[0] is None):
                return None
            default = info.params[i - offset].default
            if default is None:
                return None
            return self.substitute(default, info.receiver, slots[0]) if info.receiver else copy.deepcopy(default)

        e.bound = self.bind_arguments(e, names, default_for)
        e.py = info
        for i, (arg, want) in enumerate(zip(e.bound, wants)):
            t = self.expr(arg)
            if t == T.NOTHING:
                self.error(arg, "This gives no value, so it cannot be passed to an action.")
            if not self.same(want, t):
                if i < offset:
                    self.error(arg, f"'{e.name}' works on {self.describe(want)}, but this is {self.describe(t)}.")
                self.error(arg, f"'{e.name}' needs {self.describe(want)} for '{names[i]}', "
                                f"but this is {self.describe(t)}.")
        if info.gives == T.NOTHING:
            if want_value:
                self.error(e, f"'{e.name}' gives no value, so it cannot be used here.")
        elif not want_value:
            self.error(e, f"'{e.name}' gives a value, so this line does nothing on its own.",
                       "Use it inside 'say', 'let' or 'if'.")
        return info.gives

    def builtin_call(self, e):
        arg_types, result = L.CALLS[e.name]
        if e.named is not None:
            self.error(e, f"'{e.name}' takes its values in order, without names.",
                       f"For example: {L.EXAMPLES[e.name]}")
        if len(e.args) != len(arg_types):
            self.error(e, f"'{e.name}' needs {len(arg_types)} value(s) but you gave {len(e.args)}.",
                       f"For example: {L.EXAMPLES[e.name]}")
        types = []
        for i, (arg, want) in enumerate(zip(e.args, arg_types)):
            t = self.expr(arg)
            if e.name == "contains":        # works on text and on lists
                if i == 0 and T.is_list(t):
                    want = t
                elif i == 1 and T.is_list(types[0]):
                    want = types[0][1]
            if not self.same(want, t):
                self.error(arg, f"'{e.name}' needs {self.describe(want)} here, but this is {self.describe(t)}.",
                           f"For example: {L.EXAMPLES[e.name]}")
            types.append(t)
        return result

    def instance(self, action, types):
        key = (action.name, types)
        if key in self.instances:
            return self.instances[key]
        inst = self.instances[key] = Instance()
        ctx = FnCtx(inst, action.file)
        for pname, t in zip(action.params, types):
            ctx.scopes[0][pname] = t
        saved, self.fn = self.fn, ctx
        try:
            self.block(action.body)
            if inst.ret not in (None, T.NOTHING) and not self.ends_in_return(action.body):
                self.error(action, f"The action '{action.name}' gives back {self.describe(inst.ret)} "
                                   f"(line {inst.ret_line}), but it can also end without a 'return'.",
                           "Add a 'return' at the very end (for example 'return 0'), or an 'else' branch that returns.")
        except PlainError as err:
            if T.ANY in types:
                note = f"the action '{action.name}' is never called, so I looked at it without knowing its values"
            else:
                sig = ", ".join(f"{p}: {T.type_name(t)}" for p, t in zip(action.params, types))
                note = f"this happened inside the action '{action.name}' (called with {sig or 'no values'})"
            if note not in err.notes:
                err.notes.append(note)
            raise
        finally:
            self.fn = saved
        if inst.ret is None:
            inst.ret = T.NOTHING
        return inst

    def ends_in_return(self, body):
        """True when every way through these statements ends with a 'return'."""
        for s in body:
            if isinstance(s, (N.Return, N.Fail)):
                return True
            if isinstance(s, N.If) and s.else_body is not None \
                    and all(self.ends_in_return(b) for _cond, b in s.branches) and self.ends_in_return(s.else_body):
                return True
            if isinstance(s, N.Try) and self.ends_in_return(s.body) and self.ends_in_return(s.handler):
                return True
        return False

    def construct(self, e):
        sd = self.structs[e.name]
        layout = sd.layout
        if e.args:
            self.error(e, f"Create a '{e.name}' with named values.",
                       f"For example: {e.name}(" + ", ".join(f"{f}: ..." for f in layout) + ")")
        named = e.named if e.named is not None else []
        given = {}
        for fname, fexpr in named:
            if fname not in layout:
                self.error(fexpr, f"'{e.name}' has no field called '{fname}'.", "Its fields are: " + ", ".join(layout))
            if fname in given:
                self.error(fexpr, f"The field '{fname}' is given twice.")
            if fname in sd.readonly:
                self.error(fexpr, f"'{fname}' of a {e.name} can only be read, so it cannot be given here.")
            given[fname] = fexpr
        missing = [f for f in layout if f not in given and f not in sd.defaults and f not in sd.readonly]
        if missing:
            self.error(e, f"Missing value(s) for: {', '.join(missing)}.")
        for fname in layout:                    # a field that was left out gets its default value
            if fname not in given and fname in sd.defaults:
                named = named + [(fname, copy.deepcopy(sd.defaults[fname]))]
        e.named = named
        e.ctor = True
        for fname, fexpr in named:
            self.expect_type(layout[fname], self.expr(fexpr), fexpr, f"the field '{fname}'")
        return T.struct(e.name)


def check_program(program):
    Checker(program).check()
