"""Syntax tree (AST) nodes produced by the parser."""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass(kw_only=True)
class Node:
    line: int = 0
    col: int = 0
    file: Optional[str] = None      # the file of a definition that was imported (None: the program itself)


# ---- expressions -----------------------------------------------------------

@dataclass
class Num(Node):
    value: float


@dataclass
class Str(Node):
    value: str


@dataclass
class Bool(Node):
    value: bool


@dataclass
class Nothing(Node):
    pass


@dataclass
class Var(Node):
    name: str


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Unary(Node):
    op: str
    operand: Node


@dataclass
class Field(Node):
    name: str
    obj: Node


@dataclass
class Index(Node):
    obj: Node
    index: Node


@dataclass
class Call(Node):
    name: str
    args: List[Node] = field(default_factory=list)
    # For constructors such as Player(x: 1): list of (field name, expression).
    named: Optional[List[Tuple[str, Node]]] = None
    # For a sentence of a module (open window ...): the module's name. `name` is then the Python function.
    module: Optional[str] = None


@dataclass
class Input(Node):
    prompt: Node
    as_number: bool = False


@dataclass
class ListInit(Node):
    element_type: Any


# ---- statements ------------------------------------------------------------

@dataclass
class Let(Node):
    name: str
    value: Node
    fixed: bool = False         # let pi be 3.14 fixed: the name can never be changed


@dataclass
class Fail(Node):
    value: Node                 # fail "message": stop with an error that 'try' can catch


@dataclass
class Set(Node):
    target: Node
    value: Node


@dataclass
class Say(Node):
    value: Node


@dataclass
class If(Node):
    branches: List[Tuple[Node, List[Node]]]
    else_body: Optional[List[Node]] = None


@dataclass
class Repeat(Node):
    count: Node
    body: List[Node]


@dataclass
class While(Node):
    cond: Node
    body: List[Node]


@dataclass
class ForEach(Node):
    var: str
    iterable: Node
    body: List[Node]


@dataclass
class ForCount(Node):
    var: str
    start: Node
    stop: Node
    step: Optional[Node]
    body: List[Node]


@dataclass
class Stop(Node):
    pass


@dataclass
class Skip(Node):
    pass


@dataclass
class Return(Node):
    value: Optional[Node] = None


@dataclass
class ExprStmt(Node):
    expr: Node


@dataclass
class Add(Node):
    item: Node
    target: Node


@dataclass
class Remove(Node):
    item: Node
    target: Node


@dataclass
class RemoveAt(Node):
    index: Node
    target: Node


@dataclass
class Sort(Node):
    target: Node


@dataclass
class Try(Node):
    body: List[Node]
    error_name: str
    handler: List[Node]


@dataclass
class ActionDef(Node):
    name: str
    params: List[str]
    body: List[Node]


@dataclass
class DefineStruct(Node):
    name: str
    fields: List[Tuple[str, Any, int]]  # (field name, type, line)


@dataclass
class Program(Node):
    body: List[Node]
    imports: List[str] = field(default_factory=list)
