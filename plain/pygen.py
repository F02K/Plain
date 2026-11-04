"""Python backend: writes a standalone Python program from the syntax tree.

Type checking is done by the normal compiler first (see toolchain.py), so a
program that is rejected for the native target is rejected here too.
"""

from . import nodes as N
from .pyruntime import PRELUDE


def var(name):
    return "v_" + name


class PyGen:
    def __init__(self, program):
        self.program = program
        self.out = []

    def line(self, indent, text):
        self.out.append("    " * indent + text)

    def generate(self):
        self.out.append(PRELUDE)
        for stmt in self.program.body:
            if isinstance(stmt, N.DefineStruct):
                self.struct(stmt)
        for stmt in self.program.body:
            if isinstance(stmt, N.ActionDef):
                self.action(stmt)
        self.line(0, "")
        self.line(0, "")
        self.line(0, "def _main():")
        body = [s for s in self.program.body if not isinstance(s, (N.DefineStruct, N.ActionDef))]
        self.block(body, 1)
        self.line(0, "")
        self.line(0, "")
        self.line(0, 'if __name__ == "__main__":')
        self.line(1, "_run(_main)")
        return "\n".join(self.out) + "\n"

    # ---- definitions ---------------------------------------------------------

    def struct(self, s):
        names = [f"f_{name}" for name, _, _ in s.fields]
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"class T_{s.name}:")
        self.line(1, "__slots__ = (" + "".join(f'"{n}", ' for n in names) + ")")
        self.line(1, "def __init__(self, " + ", ".join(names) + "):")
        for n in names:
            self.line(2, f"self.{n} = {n}")

    def action(self, a):
        self.line(0, "")
        self.line(0, "")
        self.line(0, f"def a_{a.name}(" + ", ".join(var(p) for p in a.params) + "):")
        self.block(a.body, 1)

    # ---- statements ----------------------------------------------------------

    def block(self, body, indent):
        before = len(self.out)
        for stmt in body:
            getattr(self, "s_" + type(stmt).__name__)(stmt, indent)
        if len(self.out) == before:
            self.line(indent, "pass")

    def s_Let(self, s, i):
        value = "[]" if isinstance(s.value, N.ListInit) else self.expr(s.value)
        self.line(i, f"{var(s.name)} = {value}")

    def s_Set(self, s, i):
        t = s.target
        if isinstance(t, N.Var):
            self.line(i, f"{var(t.name)} = {self.expr(s.value)}")
        elif isinstance(t, N.Field):
            self.line(i, f'setattr({self.expr(t.obj)}, "f_{t.name}", {self.expr(s.value)})')
        else:
            self.line(i, f"_set({self.expr(t.obj)}, {self.expr(t.index)}, {self.expr(s.value)}, {s.line})")

    def s_Say(self, s, i):
        v = s.value
        text = v.value if isinstance(v, N.Str) else None
        self.line(i, f"print({self.expr(v) if text is not None else '_fmt(' + self.expr(v) + ')'})")

    def s_If(self, s, i):
        for n, (cond, body) in enumerate(s.branches):
            self.line(i, ("if " if n == 0 else "elif ") + self.expr(cond) + ":")
            self.block(body, i + 1)
        if s.else_body is not None:
            self.line(i, "else:")
            self.block(s.else_body, i + 1)

    def s_Repeat(self, s, i):
        self.line(i, f"for _ in range(int({self.expr(s.count)})):")
        self.block(s.body, i + 1)

    def s_While(self, s, i):
        self.line(i, f"while {self.expr(s.cond)}:")
        self.block(s.body, i + 1)

    def s_ForEach(self, s, i):
        self.line(i, f"for {var(s.var)} in {self.expr(s.iterable)}:")
        self.block(s.body, i + 1)

    def s_Stop(self, s, i):
        self.line(i, "break")

    def s_Skip(self, s, i):
        self.line(i, "continue")

    def s_Return(self, s, i):
        self.line(i, "return" if s.value is None else f"return {self.expr(s.value)}")

    def s_ExprStmt(self, s, i):
        self.line(i, self.expr(s.expr))

    def s_Add(self, s, i):
        self.line(i, f"{self.expr(s.target)}.append({self.expr(s.item)})")

    def s_Remove(self, s, i):
        self.line(i, f"_remove({self.expr(s.target)}, {self.expr(s.item)})")

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
        if e.named is not None:
            args = ", ".join(f"f_{n}={self.expr(v)}" for n, v in e.named)
            return f"T_{e.name}({args})"
        return f"a_{e.name}(" + ", ".join(self.expr(a) for a in e.args) + ")"


def generate_python(program):
    return PyGen(program).generate()
