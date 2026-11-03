"""Error type and friendly error formatting for the Plain compiler."""


class PlainError(Exception):
    """A problem in the user's program, reported in beginner-friendly words."""

    def __init__(self, message, line=None, col=None, hint=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.notes = []


def format_error(err, source, filename):
    """Render an error with the offending source line and a pointer."""
    out = []
    where = filename if err.line is None else f"{filename}, line {err.line}"
    out.append(f"Error in {where}:")
    if err.line is not None:
        lines = source.splitlines()
        if 1 <= err.line <= len(lines):
            text = lines[err.line - 1]
            out.append(f"  {err.line:>3} | {text}")
            if err.col is not None:
                out.append("      | " + " " * (err.col - 1) + "^")
    out.append(err.message)
    if err.hint:
        out.append(f"Hint: {err.hint}")
    for note in err.notes:
        out.append(f"Note: {note}")
    return "\n".join(out)
