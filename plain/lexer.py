"""Lexer: turns source text into tokens."""

from dataclasses import dataclass
from .errors import PlainError

KEYWORDS = {
    "let", "be", "set", "to", "say", "input",
    "if", "then", "else", "end",
    "repeat", "times", "while", "do", "for", "each", "in",
    "stop", "skip", "action", "return",
    "define", "as", "list", "of", "at", "add", "remove", "from", "sort",
    "try", "catch",
    "and", "or", "not", "mod",
    "true", "false", "nothing",
}


@dataclass
class Token:
    kind: str  # NUMBER, TEXT, NAME, KEYWORD, SYMBOL, NEWLINE, EOF
    value: object
    line: int
    col: int

    def is_kw(self, *words):
        return self.kind == "KEYWORD" and self.value in words

    def is_sym(self, *symbols):
        return self.kind == "SYMBOL" and self.value in symbols


def describe(tok):
    """Describe a token in plain words for error messages."""
    if tok.kind == "NEWLINE":
        return "the end of the line"
    if tok.kind == "EOF":
        return "the end of the file"
    if tok.kind == "TEXT":
        return f'the text "{tok.value}"'
    if tok.kind == "NUMBER":
        return f"the number {tok.value:g}"
    return f"'{tok.value}'"


ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def tokenize(src):
    tokens = []
    i = 0
    n = len(src)
    line = 1
    line_start = 0
    depth = 0  # parenthesis depth; line breaks inside () are ignored

    def err(msg, at, hint=None):
        raise PlainError(msg, line, at - line_start + 1, hint)

    while i < n:
        c = src[i]
        col = i - line_start + 1

        if c == "\n":
            if depth == 0 and tokens and tokens[-1].kind != "NEWLINE":
                tokens.append(Token("NEWLINE", "\n", line, col))
            i += 1
            line += 1
            line_start = i
            continue
        if c in " \t\r":
            i += 1
            continue

        if c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j + 1 < n and src[j] == "." and src[j + 1].isdigit():
                j += 1
                while j < n and src[j].isdigit():
                    j += 1
            if j < n and (src[j].isalpha() or src[j] == "_"):
                err("A name cannot start with a digit.", i,
                    "Names start with a letter, for example: player1")
            tokens.append(Token("NUMBER", float(src[i:j]), line, col))
            i = j
            continue

        if c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            if word == "note" and j < n and src[j] == ":":
                while j < n and src[j] != "\n":  # comment until end of line
                    j += 1
                i = j
                continue
            kind = "KEYWORD" if word in KEYWORDS else "NAME"
            tokens.append(Token(kind, word, line, col))
            i = j
            continue

        if c == '"':
            j = i + 1
            chars = []
            while True:
                if j >= n or src[j] == "\n":
                    err("This text is missing its closing quote (\").", i)
                ch = src[j]
                if ch == '"':
                    break
                if ch == "\\":
                    if j + 1 >= n or src[j + 1] not in ESCAPES:
                        err("Unknown escape after a backslash.", j,
                            'Use \\n (new line), \\t (tab), \\" (quote) or \\\\ (backslash).')
                    chars.append(ESCAPES[src[j + 1]])
                    j += 2
                    continue
                chars.append(ch)
                j += 1
            tokens.append(Token("TEXT", "".join(chars), line, col))
            i = j + 1
            continue

        two = src[i:i + 2]
        if two == "==":
            err("'==' is not used in Plain.", i, "To compare two values write a single '=': if a = b then")
        if two == "!=" or two == "<>":
            err(f"'{two}' is not used in Plain.", i, "Write: if not (a = b) then")
        if two in ("<=", ">="):
            tokens.append(Token("SYMBOL", two, line, col))
            i += 2
            continue
        if c in "+-*/<>=,:":
            tokens.append(Token("SYMBOL", c, line, col))
            i += 1
            continue
        if c in "()":
            depth += 1 if c == "(" else -1
            depth = max(depth, 0)
            tokens.append(Token("SYMBOL", c, line, col))
            i += 1
            continue

        err(f"I don't understand the character '{c}'.", i)

    if tokens and tokens[-1].kind != "NEWLINE":
        tokens.append(Token("NEWLINE", "\n", line, n - line_start + 1))
    tokens.append(Token("EOF", None, line, n - line_start + 1))
    return tokens
