"""Python writer: turns the syntax tree into a standalone Python program.

The checker has already accepted the program (see toolchain.py).
"""

import os

from . import library as L
from . import nodes as N
from . import modules as M
from .pyruntime import PRELUDE, WATCH_PRELUDE


def var(name):
    return "v_" + name


class PyGen:
    def __init__(self, program, watch=False):
        self.program = program
        self.out = []
        self.watch = watch
        self.scope = ""   # name of the action being written, for the watcher
        self.constants = getattr(program, "constants", [])      # set by the checker

    def line(self, indent, text):
        self.out.append("    " * indent + text)

    def generate(self):
        self.out.append(PRELUDE)
        for ns, path in getattr(self.program, "pyfiles", {}).items():
            self.python_module(ns, path)
        for stmt in self.program.body:
            if isinstance(stmt, N.DefineStruct):
                self.struct(stmt)
        for stmt in self.constants:             # 'let ... fixed' values that actions can read: made first
            self.line(0, "")
            self.line(0, f"{var(stmt.name)} = {self.expr(stmt.value)}")
        for stmt in self.program.body:
            if isinstance(stmt, N.ActionDef):
                self.action(stmt)
        self.line(0, "")
        self.line(0, "")
        if self.watch:
            acts = {a.name: (a.line, tuple(a.params)) for a in self.program.body
                    if isinstance(a, N.ActionDef) and not a.file}
            self.line(0, "_ACT = " + repr(acts))
            self.line(0, "")
            self.line(0, "")
        self.line(0, "def _main():")
        body = [s for s in self.program.body
                if not isinstance(s, (N.DefineStruct, N.ActionDef, N.PythonExport, N.PythonBlock))]
        self.block(body, 1)
        self.line(0, "")
        self.line(0, "")
        self.line(0, 'if __name__ == "__main__":')
        self.line(1, "_run(_main)")
        if self.watch:
            self.out.insert(1, WATCH_PRELUDE)
        return "\n".join(self.out) + "\n"

    # ---- definitions ---------------------------------------------------------

    def python_module(self, ns, path):
        """The Python code of a module goes into the program as it is, inside a function, so that its names
        cannot clash with the program. 'ns.name' reaches what it defines."""
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"# ---- Python code of a module ({os.path.basename(path)})")
        self.line(0, f"def _make{ns}():")
        for text in M.python_source(path).splitlines():
            self.out.append(("    " + text) if text.strip() else "")
        self.line(1, 'return {k: v for k, v in locals().items() if not k.startswith("__")}')
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"{ns} = _Ns(_make{ns}())")

    def struct(self, s):
        if s.py:
            return self.python_struct(s)
        names = [f"f_{name}" for name, _, _ in s.fields]
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"class T_{s.name}:")
        self.line(1, "__slots__ = (" + "".join(f'"{n}", ' for n in names) + ")")
        self.line(1, "def __init__(self, " + ", ".join(names) + "):")
        for n in names:
            self.line(2, f"self.{n} = {n}")

    def python_struct(self, s):
        """A type that Python builds: a thin class around the Python class, so that field 'x' is Python's attribute x."""
        base = f"{s.py}.{s.name}"
        given = [f"f_{name}" for name, _, _ in s.fields if name not in s.readonly]
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"class T_{s.name}({base}):")
        self.line(1, "def __init__(self, " + ", ".join(given) + "):")
        self.line(2, f"{base}.__init__(self" + "".join(", " + g for g in given) + ")")
        for name, _, _ in s.fields:
            self.line(1, f'f_{name} = _alias("{name}"' + (", True)" if name in s.readonly else ")"))

    def action(self, a):
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"def a_{a.name}(" + ", ".join(var(p) for p in a.params) + "):")
        self.scope = a.name
        watching, self.watch = self.watch, self.watch and not a.file      # lines of other files cannot be shown
        for p in a.params:
            self.watched(1, p, a.line, note=False)
        self.block(a.body, 1)
        self.watch = watching
        self.scope = ""

    # ---- statements ----------------------------------------------------------

    def watched(self, indent, name, line, shown=None, note=True):
        """Report a variable to the IDE (only when the program is built with watch=True)."""
        if self.watch:
            label = f"{self.scope}: {name}" if self.scope else name
            if not note:
                self.line(indent, f'_wvar("{label}", {var(name)}, {line})')
            else:
                self.line(indent, f'_watch("{label}", {var(name)}, {line}' + (f", {shown})" if shown else ")"))

    def traced(self, node, code, prefix=None):
        """Wrap an expression so the IDE can show its result next to the line."""
        if not self.watch:
            return code
        extra = f", {prefix!r}" if prefix else ""
        return f"_tr({node.line}, {code}{extra})"

    def watch_list(self, indent, target, line):
        root = target
        while not isinstance(root, N.Var) and hasattr(root, "obj"):
            root = root.obj
        if isinstance(root, N.Var):
            self.watched(indent, root.name, line)

    def block(self, body, indent):
        before = len(self.out)
        for stmt in body:
            getattr(self, "s_" + type(stmt).__name__)(stmt, indent)
        if len(self.out) == before:
            self.line(indent, "pass")

    def s_Let(self, s, i):
        if s in self.constants:
            return
        value = "[]" if isinstance(s.value, N.ListInit) else self.expr(s.value)
        self.line(i, f"{var(s.name)} = {value}")
        self.watched(i, s.name, s.line)

    def s_Set(self, s, i):
        t = s.target
        value = self.expr(s.value)
        inner = self.watch and not isinstance(t, N.Var)
        if inner:
            value = f"(_v := {value})"      # keep the new value so the IDE can show it
        if isinstance(t, N.Var):
            self.line(i, f"{var(t.name)} = {value}")
        elif isinstance(t, N.Field):
            self.line(i, f'setattr({self.expr(t.obj)}, "f_{t.name}", {value})')
        else:
            self.line(i, f"_set({self.expr(t.obj)}, {self.expr(t.index)}, {value}, {s.line})")
        root = t
        while not isinstance(root, N.Var) and hasattr(root, "obj"):
            root = root.obj
        if isinstance(root, N.Var):
            self.watched(i, root.name, s.line, shown="_v" if inner else None)

    def s_Say(self, s, i):
        v = s.value
        text = v.value if isinstance(v, N.Str) else None
        if text is not None:
            self.line(i, f"print({self.expr(v)})")
        else:
            self.line(i, f"print(_fmt({self.traced(v, self.expr(v))}))")

    def s_If(self, s, i):
        for n, (cond, body) in enumerate(s.branches):
            self.line(i, ("if " if n == 0 else "elif ") + self.traced(cond, self.expr(cond)) + ":")
            self.block(body, i + 1)
        if s.else_body is not None:
            self.line(i, "else:")
            self.block(s.else_body, i + 1)

    def s_Repeat(self, s, i):
        self.line(i, f"for _ in range(int({self.expr(s.count)})):")
        self.block(s.body, i + 1)

    def s_While(self, s, i):
        self.line(i, f"while {self.traced(s.cond, self.expr(s.cond))}:")
        self.block(s.body, i + 1)

    def s_ForEach(self, s, i):
        self.line(i, f"for {var(s.var)} in {self.expr(s.iterable)}:")
        self.watched(i + 1, s.var, s.line)
        self.block(s.body, i + 1)

    def s_ForCount(self, s, i):
        step = self.expr(s.step) if s.step is not None else "1.0"
        self.line(i, f"for {var(s.var)} in _count({self.expr(s.start)}, {self.expr(s.stop)}, {step}, {s.line}):")
        self.watched(i + 1, s.var, s.line)
        self.block(s.body, i + 1)

    def s_Wait(self, s, i):
        self.line(i, f"_wait({self.expr(s.seconds)}, {s.line})")

    def s_Fail(self, s, i):
        self.line(i, f"raise _PlainError({self.expr(s.value)}, {s.line})")

    def s_Stop(self, s, i):
        self.line(i, "break")

    def s_Skip(self, s, i):
        self.line(i, "continue")

    def s_Return(self, s, i):
        self.line(i, "return" if s.value is None
                  else f"return {self.traced(s.value, self.expr(s.value), 'returns ')}")

    def s_ExprStmt(self, s, i):
        self.line(i, self.expr(s.expr))

    def s_Add(self, s, i):
        self.line(i, f"{self.expr(s.target)}.append({self.expr(s.item)})")
        self.watch_list(i, s.target, s.line)

    def s_Remove(self, s, i):
        self.line(i, f"_remove({self.expr(s.target)}, {self.expr(s.item)})")
        self.watch_list(i, s.target, s.line)

    def s_RemoveAt(self, s, i):
        self.line(i, f"_remove_at({self.expr(s.target)}, {self.expr(s.index)}, {s.line})")
        self.watch_list(i, s.target, s.line)

    def s_Sort(self, s, i):
        self.line(i, f"{self.expr(s.target)}.sort()")
        self.watch_list(i, s.target, s.line)

    def s_Try(self, s, i):
        self.line(i, "try:")
        self.block(s.body, i + 1)
        self.line(i, "except _PlainError as _err:")
        self.line(i + 1, f"{var(s.error_name)} = _err.message")
        self.block(s.handler, i + 1)

    # ---- expressions ---------------------------------------------------------

    def expr(self, e):
        return getattr(self, "x_" + type(e).__name__)(e)

    def x_Num(self, e):
        return repr(float(e.value))

    def x_Str(self, e):
        return repr(e.value)

    def x_Bool(self, e):
        return "True" if e.value else "False"

    def x_Nothing(self, e):
        return "None"

    def x_Var(self, e):
        return var(e.name)

    def x_Unary(self, e):
        return f"(not {self.expr(e.operand)})" if e.op == "not" else f"(-{self.expr(e.operand)})"

    def x_Input(self, e):
        if e.as_number:
            return f"_input_number({self.expr(e.prompt)}, {e.line})"
        return f"_input({self.expr(e.prompt)})"

    def x_Field(self, e):
        obj = self.expr(e.obj)
        if e.name == "size":
            return f'_size_or_field({obj}, "f_size")'
        if e.name in L.OF:
            return f'_of("{e.name}", _{e.name}, {obj}, {e.line})'
        return f"{obj}.f_{e.name}"

    def x_Index(self, e):
        return f"_get({self.expr(e.obj)}, {self.expr(e.index)}, {e.line})"

    def x_Binary(self, e):
        l, r, op = self.expr(e.left), self.expr(e.right), e.op
        if op == "+":
            return f"_add({l}, {r})"
        if op == "=":
            return f"_eq({l}, {r})"
        if op == "/":
            return f"_div({l}, {r}, {e.line})"
        if op == "mod":
            return f"_mod({l}, {r}, {e.line})"
        return f"({l} {op} {r})"

    def x_Call(self, e):
        if e.py is not None:       # an action of a module: its Python function gets the line number last
            fn = f"{e.py.ns}.{e.name}"
            if self.watch:
                return f"_tg({e.line}, {fn}" + "".join(", " + self.expr(a) for a in e.bound) + ")"
            return f"{fn}(" + ", ".join([self.expr(a) for a in e.bound] + [str(e.line)]) + ")"
        if e.name in L.CALLS:
            return f"_{e.name}(" + ", ".join([self.expr(a) for a in e.args] + [str(e.line)]) + ")"
        if e.ctor:
            args = ", ".join(f"f_{n}={self.expr(v)}" for n, v in e.named)
            return f"T_{e.name}({args})"
        values = e.bound if e.bound is not None else e.args
        if self.watch:
            return f'_tc({e.line}, "{e.name}", a_{e.name}' + "".join(", " + self.expr(a) for a in values) + ")"
        return f"a_{e.name}(" + ", ".join(self.expr(a) for a in values) + ")"


def generate_python(program, watch=False):
    return PyGen(program, watch).generate()
