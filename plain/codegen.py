"""Code generator: checks types and writes NASM assembly (x64).

How it works, in short:
  * Every value lives in one 64-bit slot. The result of an expression is in rax.
  * Types are found automatically. Actions have no type annotations, so an
    action is compiled separately for each combination of argument types it is
    called with (like a template). Nothing is decided at run time.
  * Local variables live in the stack frame at [rbp - 8 * n].
  * Arguments for actions are pushed on the stack; the result comes back in rax.
"""

import difflib
import struct as pystruct

from . import nodes as N
from . import typesys as T
from .errors import PlainError
from . import runtime_asm as RT
from . import library as L


class FnCtx:
    """State for the function that is currently being compiled."""

    def __init__(self, label, name, inst=None):
        self.label = label
        self.name = name
        self.inst = inst
        self.lines = []
        self.nslots = 0
        self.scopes = [{}]
        self.depth = 0          # number of 8-byte pushes currently on the stack
        self.loops = []         # (stop label, skip label, try depth)
        self.try_depth = 0
        self.is_main = inst is None


class Instance:
    def __init__(self, label):
        self.label = label
        self.ret = None         # None while still being compiled


class Compiler:
    def __init__(self, program, target):
        self.program = program
        self.target = target    # "linux" or "windows"
        self.structs = {}
        self.actions = {}
        self.instances = {}
        self.strings = {}
        self.functions = []
        self.uses_gfx = False
        self.label_count = 0
        self.fn = None

    # ---- small helpers -------------------------------------------------------

    def error(self, node, message, hint=None):
        raise PlainError(message, getattr(node, "line", None) or None,
                         getattr(node, "col", None) or None, hint)

    def emit(self, text):
        self.fn.lines.append("    " + text)

    def label(self, name):
        self.fn.lines.append(name + ":")

    def new_label(self, prefix="L"):
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def new_slot(self):
        self.fn.nslots += 1
        return f"[rbp - {8 * self.fn.nslots}]"

    def push(self):
        self.emit("push rax")
        self.fn.depth += 1

    def call_rt(self, name):
        """Call a runtime routine, keeping the stack 16-byte aligned."""
        if self.fn.depth % 2:
            self.emit("sub rsp, 8")
            self.emit(f"call {name}")
            self.emit("add rsp, 8")
        else:
            self.emit(f"call {name}")

    def runtime_error(self, message_label, node):
        self.emit(f"lea A1, [rel {message_label}]")
        self.emit(f"mov A2, {node.line}")
        self.call_rt("rt_error")

    def string_label(self, text):
        data = text.encode("utf-8")
        if data not in self.strings:
            self.strings[data] = f"str_{len(self.strings)}"
        return self.strings[data]

    def check_type(self, t, node):
        if T.is_list(t):
            self.check_type(t[1], node)
        elif T.is_struct(t) and t[1] not in self.structs:
            names = list(self.structs)
            hint = None
            close = difflib.get_close_matches(t[1], names, n=1)
            if close:
                hint = f"Did you mean '{close[0]}'?"
            self.error(node, f"I don't know a type called '{t[1]}'.", hint)
        return t

    # ---- scopes --------------------------------------------------------------

    def declare(self, name, t, operand, node):
        for scope in self.fn.scopes:
            if name in scope:
                self.error(node, f"There is already a variable called '{name}'.",
                           f"To change it use: set {name} to ...")
        self.fn.scopes[-1][name] = (t, operand)

    def lookup(self, name, node):
        for scope in reversed(self.fn.scopes):
            if name in scope:
                return scope[name]
        known = [n for sc in self.fn.scopes for n in sc]
        hint = None
        close = difflib.get_close_matches(name, known, n=1)
        if close:
            hint = f"Did you mean '{close[0]}'?"
        elif not self.fn.is_main:
            hint = "An action only knows its own parameters and variables. Pass other values in as parameters."
        else:
            hint = f"Create it first with: let {name} be ..."
        self.error(node, f"I don't know a variable called '{name}'.", hint)

    # ---- program -------------------------------------------------------------

    def compile(self):
        self.collect_definitions()
        main = FnCtx("plain_main", "main")
        self.fn = main
        for stmt in self.program.body:
            if isinstance(stmt, (N.DefineStruct, N.ActionDef)):
                continue
            self.statement(stmt)
        self.finish(main)
        return self.assemble()

    def collect_definitions(self):
        for stmt in self.program.body:
            if isinstance(stmt, N.DefineStruct):
                if stmt.name in self.structs or stmt.name in T.PRIMITIVES or stmt.name == "nothing" \
                        or stmt.name in L.CALLS:
                    self.error(stmt, f"The type '{stmt.name}' is defined twice or is a built-in name.")
                self.structs[stmt.name] = stmt
        for stmt in self.program.body:
            if isinstance(stmt, N.ActionDef):
                if stmt.name in L.CALLS:
                    self.error(stmt, f"'{stmt.name}' is a built-in helper, so it cannot be used as an action name.",
                               "Pick another name.")
                if stmt.name in self.actions or stmt.name in self.structs:
                    self.error(stmt, f"The name '{stmt.name}' is already used by an action or a type.")
                if len(set(stmt.params)) != len(stmt.params):
                    self.error(stmt, "Two parameters have the same name.")
                self.actions[stmt.name] = stmt
        # Resolve field layouts after all type names are known.
        for name, sd in list(self.structs.items()):
            fields = {}
            if not sd.fields:
                self.error(sd, f"The type '{name}' has no fields.")
            for i, (fname, ftype, fline) in enumerate(sd.fields):
                if fname in fields:
                    raise PlainError(f"The field '{fname}' appears twice in '{name}'.", fline)
                self.check_type(ftype, N.Node(line=fline))
                fields[fname] = (8 * i, ftype)
            sd.layout = fields

    def finish(self, ctx):
        """Wrap the body of a function with prologue and epilogue."""
        frame = ((8 * ctx.nslots + 15) // 16) * 16
        head = [f"{ctx.label}:", "    push rbp", "    mov rbp, rsp"]
        if frame:
            head.append(f"    sub rsp, {frame}")
        tail = ["    xor eax, eax", "    leave", "    ret", ""]
        ctx.lines = head + ctx.lines + tail
        self.functions.append(ctx)

    def assemble(self):
        out = []
        out.append("; Generated by the Plain compiler. Target: " + self.target)
        out.append("%define " + ("WINDOWS" if self.target == "windows" else "LINUX"))
        out.append(RT.HEADER)
        externs = list(RT.EXTERNS_COMMON)
        if self.target == "windows":
            externs.append("SetConsoleOutputCP")
        if self.uses_gfx:
            externs += RT.GFX_EXTERNS
        for name in externs:
            out.append(f"extern {name}")
        out.append("")
        out.append("section .text")
        out.append("global main")
        out.append("main:")
        out.append("    push rbp")
        out.append("    mov rbp, rsp")
        out.append("    sub rsp, 32")
        if self.target == "windows":
            out.append("    mov ecx, 65001")
            out.append("    call SetConsoleOutputCP")
        out.append("    call plain_main")
        if self.uses_gfx:
            out.append("    call rt_gfx_finish")
        out.append("    xor eax, eax")
        out.append("    leave")
        out.append("    ret")
        out.append("")
        for ctx in self.functions:
            out.append(f"; ---- {ctx.name} ----")
            out.extend(ctx.lines)
        out.append(RT.RUNTIME)
        if self.uses_gfx:
            out.append(RT.GFX_RUNTIME)
        out.append("section .data")
        out.append(RT.DATA)
        if self.uses_gfx:
            out.append(RT.GFX_DATA)
        for data, label in self.strings.items():
            bytes_ = list(data) + [0]
            out.append(f"{label}: db " + ", ".join(str(b) for b in bytes_))
        out.append("")
        out.append("section .bss")
        out.append(RT.BSS)
        if self.uses_gfx:
            out.append(RT.GFX_BSS)
        if self.target == "linux":
            out.append("section .note.GNU-stack noalloc noexec nowrite progbits")
        return "\n".join(out) + "\n"

    # ---- statements ----------------------------------------------------------

    def block(self, body):
        self.fn.scopes.append({})
        for stmt in body:
            self.statement(stmt)
        self.fn.scopes.pop()

    def statement(self, stmt):
        getattr(self, "s_" + type(stmt).__name__)(stmt)

    def s_Group(self, s):
        for stmt in s.body:
            self.statement(stmt)

    def s_Let(self, s):
        if isinstance(s.value, N.ListInit):
            t = T.list_of(self.check_type(s.value.element_type, s.value))
            self.emit("mov A1, 24")
            self.call_rt("rt_alloc")
        else:
            t = self.expr(s.value)
            if t == T.NOTHING:
                self.error(s.value, "This gives no value, so it cannot be stored in a variable.")
        slot = self.new_slot()
        self.declare(s.name, t, slot, s)
        self.emit(f"mov {slot}, rax")

    def s_Set(self, s):
        target = s.target
        if isinstance(target, N.Var):
            vt, operand = self.lookup(target.name, target)
            t = self.expr(s.value)
            self.expect_type(vt, t, s.value, f"the variable '{target.name}'")
            self.emit(f"mov {operand}, rax")
        elif isinstance(target, N.Field):
            ot = self.expr(target.obj)
            offset, ft = self.field_info(ot, target)
            self.push()
            t = self.expr(s.value)
            self.expect_type(ft, t, s.value, f"the field '{target.name}'")
            self.emit("pop rcx")
            self.fn.depth -= 1
            self.emit(f"mov [rcx + {offset}], rax")
        else:  # Index
            lt = self.expr(target.obj)
            if not T.is_list(lt):
                self.error(target, f"'at' only works on lists, but this is {self.describe(lt)}.")
            self.push()
            it = self.expr(target.index)
            self.expect_number(it, target.index, "A list position")
            self.emit("movq xmm0, rax")
            self.emit("cvttsd2si rax, xmm0")
            self.push()
            vt = self.expr(s.value)
            self.expect_type(lt[1], vt, s.value, "this list item")
            self.emit("mov A3, rax")
            self.emit("pop A2")
            self.emit("pop A1")
            self.fn.depth -= 2
            self.emit(f"mov A4, {s.line}")
            self.call_rt("rt_list_set")

    def s_Say(self, s):
        t = self.expr(s.value)
        if t not in (T.TEXT, T.NUMBER, T.BOOLEAN, T.NOTHING):
            self.error(s.value, f"'say' cannot show {self.describe(t)} directly.",
                       "Say its fields one by one, for example: say health of player")
        self.to_text(t, s.value)
        self.emit("mov A1, rax")
        self.call_rt("rt_say")

    def s_If(self, s):
        end = self.new_label("if_end_")
        for cond, body in s.branches:
            nxt = self.new_label("if_next_")
            self.condition(cond, "An if")
            self.emit("test rax, rax")
            self.emit(f"jz {nxt}")
            self.block(body)
            self.emit(f"jmp {end}")
            self.label(nxt)
        if s.else_body is not None:
            self.block(s.else_body)
        self.label(end)

    def s_Repeat(self, s):
        t = self.expr(s.count)
        self.expect_number(t, s.count, "'repeat' needs a number, but this")
        self.emit("movq xmm0, rax")
        self.emit("cvttsd2si rax, xmm0")
        counter = self.new_slot()
        self.emit(f"mov {counter}, rax")
        top, cont, end = (self.new_label(p) for p in ("rep_top_", "rep_next_", "rep_end_"))
        self.label(top)
        self.emit(f"cmp qword {counter}, 0")
        self.emit(f"jle {end}")
        self.fn.loops.append((end, cont, self.fn.try_depth))
        self.block(s.body)
        self.fn.loops.pop()
        self.label(cont)
        self.emit(f"sub qword {counter}, 1")
        self.emit(f"jmp {top}")
        self.label(end)

    def s_While(self, s):
        top, end = self.new_label("while_top_"), self.new_label("while_end_")
        self.label(top)
        self.condition(s.cond, "A while")
        self.emit("test rax, rax")
        self.emit(f"jz {end}")
        self.fn.loops.append((end, top, self.fn.try_depth))
        self.block(s.body)
        self.fn.loops.pop()
        self.emit(f"jmp {top}")
        self.label(end)

    def s_ForEach(self, s):
        t = self.expr(s.iterable)
        if not T.is_list(t):
            self.error(s.iterable, f"'for each' needs a list, but this is {self.describe(t)}.")
        list_slot, idx_slot, var_slot = self.new_slot(), self.new_slot(), self.new_slot()
        self.emit(f"mov {list_slot}, rax")
        self.emit(f"mov qword {idx_slot}, 0")
        top, cont, end = (self.new_label(p) for p in ("each_top_", "each_next_", "each_end_"))
        self.label(top)
        self.emit(f"mov rax, {list_slot}")
        self.emit(f"mov rcx, {idx_slot}")
        self.emit("cmp rcx, [rax]")
        self.emit(f"jae {end}")
        self.emit("mov rdx, [rax + 16]")
        self.emit("mov rax, [rdx + rcx * 8]")
        self.emit(f"mov {var_slot}, rax")
        self.fn.scopes.append({})
        self.declare(s.var, t[1], var_slot, s)
        self.fn.loops.append((end, cont, self.fn.try_depth))
        self.block(s.body)
        self.fn.loops.pop()
        self.fn.scopes.pop()
        self.label(cont)
        self.emit(f"add qword {idx_slot}, 1")
        self.emit(f"jmp {top}")
        self.label(end)

    def leave_tries(self, count):
        if count:
            self.emit(f"sub qword [rel rt_hcount], {count}")

    def s_Stop(self, s):
        if not self.fn.loops:
            self.error(s, "'stop' can only be used inside a loop.")
        end, _, try_depth = self.fn.loops[-1]
        self.leave_tries(self.fn.try_depth - try_depth)
        self.emit(f"jmp {end}")

    def s_Skip(self, s):
        if not self.fn.loops:
            self.error(s, "'skip' can only be used inside a loop.")
        _, cont, try_depth = self.fn.loops[-1]
        self.leave_tries(self.fn.try_depth - try_depth)
        self.emit(f"jmp {cont}")

    def s_Return(self, s):
        if self.fn.is_main:
            self.error(s, "'return' can only be used inside an action.")
        inst = self.fn.inst
        if s.value is None:
            t = T.NOTHING
            self.emit("xor eax, eax")
        else:
            t = self.expr(s.value)
        if inst.ret is None:
            inst.ret = t
            inst.ret_line = s.line
        elif inst.ret != t:
            self.error(s, f"This action already returns {self.describe(inst.ret)} (line {inst.ret_line}), "
                          f"but here it returns {self.describe(t)}.",
                       "An action must always return the same kind of value.")
        self.leave_tries(self.fn.try_depth)
        self.emit("leave")
        self.emit("ret")

    def s_ExprStmt(self, s):
        self.call(s.expr, want_value=False)

    def s_Add(self, s):
        lt = self.expr(s.target)
        if not T.is_list(lt):
            self.error(s.target, f"'add' needs a list, but this is {self.describe(lt)}.")
        self.push()
        it = self.expr(s.item)
        self.expect_type(lt[1], it, s.item, "this list")
        self.emit("mov A2, rax")
        self.emit("pop A1")
        self.fn.depth -= 1
        self.call_rt("rt_list_add")

    def s_Remove(self, s):
        lt = self.expr(s.target)
        if not T.is_list(lt):
            self.error(s.target, f"'remove' needs a list, but this is {self.describe(lt)}.")
        self.push()
        it = self.expr(s.item)
        self.expect_type(lt[1], it, s.item, "this list")
        self.emit("mov A2, rax")
        self.emit("pop A1")
        self.fn.depth -= 1
        self.emit(f"mov A3, {1 if lt[1] == T.TEXT else 0}")
        self.call_rt("rt_list_remove")

    def s_RemoveAt(self, s):
        lt = self.expr(s.target)
        if not T.is_list(lt):
            self.error(s.target, f"'remove at' needs a list, but this is {self.describe(lt)}.")
        self.push()
        it = self.expr(s.index)
        self.expect_number(it, s.index, "A list position")
        self.emit("movq xmm0, rax")
        self.emit("cvttsd2si A2, xmm0")
        self.emit("pop A1")
        self.fn.depth -= 1
        self.emit(f"mov A3, {s.line}")
        self.call_rt("rt_list_remove_at")

    def s_Sort(self, s):
        lt = self.expr(s.target)
        if not T.is_list(lt) or lt[1] not in (T.NUMBER, T.TEXT):
            what = "a list of numbers or text" 
            self.error(s.target, f"'sort' needs {what}, but this is {self.describe(lt)}.")
        self.emit("mov A1, rax")
        self.emit(f"mov A2, {1 if lt[1] == T.TEXT else 0}")
        self.call_rt("rt_list_sort")

    def s_Try(self, s):
        catch, end = self.new_label("catch_"), self.new_label("try_end_")
        self.emit(f"TRY_ENTER {catch}")
        self.fn.try_depth += 1
        self.block(s.body)
        self.fn.try_depth -= 1
        self.leave_tries(1)
        self.emit(f"jmp {end}")
        self.label(catch)
        self.fn.scopes.append({})
        slot = self.new_slot()
        self.emit("mov rax, [rel rt_last_error]")
        self.emit(f"mov {slot}, rax")
        self.declare(s.error_name, T.TEXT, slot, s)
        self.block(s.handler)
        self.fn.scopes.pop()
        self.label(end)

    # ---- type helpers --------------------------------------------------------

    def describe(self, t):
        if t == T.NOTHING:
            return "nothing"
        if t in T.PRIMITIVES:
            return f"a {t}"
        if T.is_list(t):
            return f"a {T.type_name(t)}"
        return f"a '{t[1]}'"

    def expect_type(self, want, got, node, what):
        if want != got:
            self.error(node, f"{what.capitalize()} holds {self.describe(want)}, but this value is {self.describe(got)}.")

    def expect_number(self, t, node, what):
        if t != T.NUMBER:
            self.error(node, f"{what} must be a number, but this is {self.describe(t)}.")

    def condition(self, node, what):
        t = self.expr(node)
        if t != T.BOOLEAN:
            self.error(node, f"{what} condition must be true or false, but this is {self.describe(t)}.",
                       "Compare values with =, <, >, <= or >=")

    def field_info(self, obj_type, node):
        if not T.is_struct(obj_type):
            self.error(node, f"'{node.name} of ...' needs a thing with fields, but this is {self.describe(obj_type)}.")
        layout = self.structs[obj_type[1]].layout
        if node.name not in layout:
            hint = "Its fields are: " + ", ".join(layout)
            self.error(node, f"'{obj_type[1]}' has no field called '{node.name}'.", hint)
        return layout[node.name]

    def to_text(self, t, node):
        if t == T.TEXT:
            return
        if t == T.NUMBER:
            self.emit("mov A1, rax")
            self.call_rt("rt_num_to_text")
        elif t == T.BOOLEAN:
            self.emit("test rax, rax")
            self.emit("lea rax, [rel rt_str_true]")
            self.emit("lea rcx, [rel rt_str_false]")
            self.emit("cmovz rax, rcx")
        elif t == T.NOTHING:
            self.emit("lea rax, [rel rt_str_nothing]")
        else:
            self.error(node, f"I cannot turn {self.describe(t)} into text.")

    # ---- expressions ---------------------------------------------------------

    def expr(self, node):
        return getattr(self, "x_" + type(node).__name__)(node)

    def x_Num(self, e):
        bits = pystruct.unpack("<Q", pystruct.pack("<d", e.value))[0]
        self.emit(f"mov rax, 0x{bits:016X}")
        return T.NUMBER

    def x_Str(self, e):
        self.emit(f"lea rax, [rel {self.string_label(e.value)}]")
        return T.TEXT

    def x_Bool(self, e):
        self.emit(f"mov eax, {1 if e.value else 0}")
        return T.BOOLEAN

    def x_Nothing(self, e):
        self.emit("xor eax, eax")
        return T.NOTHING

    def x_Var(self, e):
        t, operand = self.lookup(e.name, e)
        self.emit(f"mov rax, {operand}")
        return t

    def x_ListInit(self, e):
        self.error(e, "'list of ...' can only be used directly after 'let ... be'.")

    def x_Unary(self, e):
        t = self.expr(e.operand)
        if e.op == "-":
            self.expect_number(t, e.operand, "The value after '-'")
            self.emit("mov rcx, 0x8000000000000000")
            self.emit("xor rax, rcx")
            return T.NUMBER
        if t != T.BOOLEAN:
            self.error(e.operand, f"'not' needs true or false, but this is {self.describe(t)}.")
        self.emit("xor eax, 1")
        return T.BOOLEAN

    def x_Input(self, e):
        t = self.expr(e.prompt)
        if t != T.TEXT:
            self.error(e.prompt, f"'input' needs a text, but this is {self.describe(t)}.")
        self.emit("mov A1, rax")
        if e.as_number:
            self.emit(f"mov A2, {e.line}")
            self.call_rt("rt_input_number")
            return T.NUMBER
        self.call_rt("rt_input")
        return T.TEXT

    def x_Field(self, e):
        ot = self.expr(e.obj)
        if T.is_list(ot) and e.name == "size":
            self.emit("mov rax, [rax]")
            self.emit("cvtsi2sd xmm0, rax")
            self.emit("movq rax, xmm0")
            return T.NUMBER
        if e.name in L.OF and not T.is_struct(ot):
            return self.builtin_of(e, ot)
        offset, ft = self.field_info(ot, e)
        self.emit(f"mov rax, [rax + {offset}]")
        return ft

    def builtin_of(self, e, ot):
        """'length of x', 'round of x', ...: the value is already in rax."""
        want, result = L.OF[e.name]
        if ot != want:
            self.error(e, f"'{e.name} of ...' needs {self.describe(want)}, but this is {self.describe(ot)}.")
        if e.name == "length":
            self.emit("mov A1, rax")
            self.call_rt("rt_text_length")
        elif e.name in ("upper", "lower"):
            self.emit("mov A1, rax")
            self.emit(f"mov A2, {1 if e.name == 'upper' else 0}")
            self.call_rt("rt_text_case")
        elif e.name == "round":          # half up: floor(x + 0.5)
            self.emit("movq xmm0, rax")
            self.emit("mov rcx, 0x3FE0000000000000")
            self.emit("movq xmm1, rcx")
            self.emit("addsd xmm0, xmm1")
            self.emit("roundsd xmm0, xmm0, 9")
            self.emit("movq rax, xmm0")
        elif e.name == "abs":
            self.emit("btr rax, 63")
        else:  # sqrt
            ok = self.new_label("sqrt_ok_")
            self.emit("movq xmm0, rax")
            self.emit("xorpd xmm1, xmm1")
            self.emit("ucomisd xmm0, xmm1")
            self.emit(f"jae {ok}")
            self.runtime_error("rt_msg_sqrt", e)
            self.label(ok)
            self.emit("sqrtsd xmm0, xmm0")
            self.emit("movq rax, xmm0")
        return result

    def builtin_call(self, e):
        """random(a, b), part(text, start, count), ...: values go to the argument registers."""
        arg_types, result = L.CALLS[e.name]
        if e.named is not None:
            self.error(e, f"'{e.name}' takes its values in order, without names.",
                       f"For example: {L.EXAMPLES[e.name]}")
        n = len(arg_types)
        if len(e.args) != n:
            self.error(e, f"'{e.name}' needs {n} value(s) but you gave {len(e.args)}.",
                       f"For example: {L.EXAMPLES[e.name]}")
        types = []
        for i, (arg, want) in enumerate(zip(e.args, arg_types)):
            t = self.expr(arg)
            if e.name == "contains":        # works on text and on lists
                if i == 0 and T.is_list(t):
                    want = t
                elif i == 1 and T.is_list(types[0]):
                    want = types[0][1]
            if t != want:
                self.error(arg, f"'{e.name}' needs {self.describe(want)} here, but this is {self.describe(t)}.",
                           f"For example: {L.EXAMPLES[e.name]}")
            types.append(t)
            self.push()
        for i in reversed(range(n)):
            self.emit(f"pop A{i + 1}")
        self.fn.depth -= n
        if e.name in L.NEEDS_LINE:
            self.emit(f"mov A{n + 1}, {e.line}")
        if e.name in L.GFX:
            if self.target == "linux":
                self.error(e, "Program windows are not available in the Assembly backend on Linux yet.",
                           "Run the program with the Python backend: plain run <file> --backend python")
            self.uses_gfx = True
            self.emit(f"mov qword [rel rt_line], {e.line}")
            self.call_rt("rt_gfx_" + e.name)
        elif e.name in ("min", "max"):
            self.emit("movq xmm0, A1")
            self.emit("movq xmm1, A2")
            self.emit(f"{e.name}sd xmm0, xmm1")
            self.emit("movq rax, xmm0")
        elif e.name == "contains" and T.is_list(types[0]):
            self.emit(f"mov A3, {1 if types[0][1] == T.TEXT else 0}")
            self.call_rt("rt_list_contains")
        else:
            self.call_rt({"random": "rt_random", "part": "rt_text_part", "contains": "rt_text_contains"}[e.name])
        return result

    def x_Index(self, e):
        lt = self.expr(e.obj)
        if not T.is_list(lt):
            self.error(e, f"'at' only works on lists, but this is {self.describe(lt)}.")
        self.push()
        it = self.expr(e.index)
        self.expect_number(it, e.index, "A list position")
        self.emit("movq xmm0, rax")
        self.emit("cvttsd2si A2, xmm0")
        self.emit("pop A1")
        self.fn.depth -= 1
        self.emit(f"mov A3, {e.line}")
        self.call_rt("rt_list_get")
        return lt[1]

    def x_Binary(self, e):
        op = e.op
        if op in ("and", "or"):
            end = self.new_label("logic_end_")
            self.condition_operand(e.left, op)
            self.emit("test rax, rax")
            self.emit(f"{'jz' if op == 'and' else 'jnz'} {end}")
            self.condition_operand(e.right, op)
            self.label(end)
            return T.BOOLEAN

        lt = self.expr(e.left)
        self.push()
        rt = self.expr(e.right)

        if op == "+" and (lt == T.TEXT or rt == T.TEXT):
            return self.concat(e, lt, rt)

        if op in ("=",):
            if lt != rt:
                self.error(e, f"I cannot compare {self.describe(lt)} with {self.describe(rt)}.")
            if lt == T.TEXT:
                self.emit("mov A2, rax")
                self.emit("pop A1")
                self.fn.depth -= 1
                self.call_rt("rt_text_eq")
                return T.BOOLEAN
            self.emit("mov rcx, rax")
            self.emit("pop rax")
            self.fn.depth -= 1
            if lt == T.NUMBER:
                self.emit("movq xmm0, rax")
                self.emit("movq xmm1, rcx")
                self.emit("ucomisd xmm0, xmm1")
                self.emit("sete al")
            else:
                self.emit("cmp rax, rcx")
                self.emit("sete al")
            self.emit("movzx eax, al")
            return T.BOOLEAN

        if lt != T.NUMBER or rt != T.NUMBER:
            hint = None
            if op == "+":
                hint = "'+' adds numbers or joins text."
            self.error(e, f"'{op}' needs two numbers, but I got {self.describe(lt)} and {self.describe(rt)}.", hint)

        self.emit("mov rcx, rax")
        self.emit("pop rax")
        self.fn.depth -= 1
        if op in ("<", ">", "<=", ">="):
            setcc = {"<": "setb", ">": "seta", "<=": "setbe", ">=": "setae"}[op]
            self.emit("movq xmm0, rax")
            self.emit("movq xmm1, rcx")
            self.emit("ucomisd xmm0, xmm1")
            self.emit(f"{setcc} al")
            self.emit("movzx eax, al")
            return T.BOOLEAN
        if op == "mod":
            self.zero_check(e, "rt_msg_mod0")
            self.emit("mov A2, rcx")
            self.emit("mov A1, rax")
            self.call_rt("rt_mod")
            return T.NUMBER
        self.emit("movq xmm0, rax")
        self.emit("movq xmm1, rcx")
        if op == "/":
            self.zero_check(e, "rt_msg_div0")
            self.emit("divsd xmm0, xmm1")
        else:
            self.emit({"+": "addsd", "-": "subsd", "*": "mulsd"}[op] + " xmm0, xmm1")
        self.emit("movq rax, xmm0")
        return T.NUMBER

    def condition_operand(self, node, op):
        t = self.expr(node)
        if t != T.BOOLEAN:
            self.error(node, f"'{op}' needs true or false on both sides, but this is {self.describe(t)}.",
                       "For example: health > 0 and health < 100")

    def zero_check(self, node, message_label):
        """Stop with an error if the divisor in rcx is zero."""
        ok = self.new_label("nonzero_")
        self.emit("movq xmm2, rcx")
        self.emit("xorpd xmm3, xmm3")
        self.emit("ucomisd xmm2, xmm3")
        self.emit(f"jne {ok}")
        self.runtime_error(message_label, node)
        self.label(ok)

    def concat(self, e, lt, rt):
        for t, side in ((lt, e.left), (rt, e.right)):
            if t not in (T.TEXT, T.NUMBER, T.BOOLEAN):
                self.error(side, f"I cannot join text with {self.describe(t)}.")
        self.to_text(rt, e.right)
        self.push()                     # right (as text) on top, left below
        self.emit("mov rax, [rsp + 8]")
        self.to_text(lt, e.left)
        self.emit("mov [rsp + 8], rax")
        self.emit("pop A2")
        self.emit("pop A1")
        self.fn.depth -= 2
        self.call_rt("rt_concat")
        return T.TEXT

    def x_Call(self, e):
        return self.call(e, want_value=True)

    def call(self, e, want_value):
        if e.name in L.CALLS:
            if not want_value and L.CALLS[e.name][1] != T.NOTHING:
                self.error(e, f"'{e.name}' gives a value, so this line does nothing on its own.",
                           "Use it inside 'say' or 'let', for example: say " + L.EXAMPLES[e.name])
            return self.builtin_call(e)
        if e.name in self.structs:
            return self.construct(e)
        if e.name not in self.actions:
            names = list(self.actions) + list(self.structs)
            close = difflib.get_close_matches(e.name, names, n=1)
            hint = f"Did you mean '{close[0]}'?" if close else \
                f"Define it first with: action {e.name}(...) do ... end"
            self.error(e, f"I don't know an action or type called '{e.name}'.", hint)
        if e.named is not None:
            self.error(e, f"'{e.name}' is an action. Give its values in order, without names.",
                       f"For example: {e.name}(" + ", ".join(self.actions[e.name].params) + ")")
        action = self.actions[e.name]
        if len(e.args) != len(action.params):
            self.error(e, f"'{e.name}' needs {len(action.params)} value(s) "
                          f"({', '.join(action.params) or 'none'}) but you gave {len(e.args)}.")
        n = len(e.args)
        fn = self.fn
        pad = (fn.depth + n) % 2
        if pad:
            self.emit("sub rsp, 8")
            fn.depth += 1
        types = []
        for arg in e.args:
            t = self.expr(arg)
            if t == T.NOTHING:
                self.error(arg, "This gives no value, so it cannot be passed to an action.")
            self.push()
            types.append(t)
        inst = self.instance(action, tuple(types), e)
        self.emit(f"call {inst.label}")
        self.emit(f"add rsp, {8 * (n + pad)}")
        fn.depth -= n + pad
        if inst.ret is None:
            if want_value:
                self.error(e, f"I don't know yet what '{e.name}' gives back, because it calls itself "
                              "before its first 'return'.",
                           "Put a 'return' with a value (the base case) before the recursive call.")
            return T.NOTHING
        return inst.ret

    def instance(self, action, types, call_node):
        key = (action.name, types)
        if key in self.instances:
            return self.instances[key]
        inst = Instance(f"plain_act_{len(self.instances) + 1}")
        self.instances[key] = inst
        ctx = FnCtx(inst.label, f"action {action.name}({', '.join(T.type_name(t) for t in types)})", inst)
        count = len(types)
        for i, (pname, t) in enumerate(zip(action.params, types)):
            ctx.scopes[0][pname] = (t, f"[rbp + {16 + 8 * (count - 1 - i)}]")
        saved = self.fn
        self.fn = ctx
        try:
            self.block(action.body)
        except PlainError as err:
            sig = ", ".join(f"{p}: {T.type_name(t)}" for p, t in zip(action.params, types))
            note = f"this happened inside the action '{action.name}' (called with {sig or 'no values'})"
            if note not in err.notes:
                err.notes.append(note)
            raise
        finally:
            self.fn = saved
        if inst.ret is None:
            inst.ret = T.NOTHING
        self.finish(ctx)
        return inst

    def construct(self, e):
        sd = self.structs[e.name]
        layout = sd.layout
        if e.named is None:
            self.error(e, f"Create a '{e.name}' with named values.",
                       f"For example: {e.name}(" + ", ".join(f"{f}: ..." for f in layout) + ")")
        given = {}
        for fname, fexpr in e.named:
            if fname not in layout:
                self.error(fexpr, f"'{e.name}' has no field called '{fname}'.", "Its fields are: " + ", ".join(layout))
            if fname in given:
                self.error(fexpr, f"The field '{fname}' is given twice.")
            given[fname] = fexpr
        missing = [f for f in layout if f not in given]
        if missing:
            self.error(e, f"Missing value(s) for: {', '.join(missing)}.")
        self.emit(f"mov A1, {8 * len(layout)}")
        self.call_rt("rt_alloc")
        self.push()
        for fname, fexpr in e.named:
            offset, ft = layout[fname]
            t = self.expr(fexpr)
            self.expect_type(ft, t, fexpr, f"the field '{fname}'")
            self.emit("mov rcx, [rsp]")
            self.emit(f"mov [rcx + {offset}], rax")
        self.emit("pop rax")
        self.fn.depth -= 1
        return T.struct(e.name)


def compile_program(program, target):
    return Compiler(program, target).compile()
