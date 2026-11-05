"""Error type and friendly error formatting for the Plain compiler."""

import os


class PlainError(Exception):
    """A problem in the user's program, reported in beginner-friendly words."""

    def __init__(self, message, line=None, col=None, hint=None, file=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.file = file            # the imported file the problem is in (None: the program itself)
        self.notes = []


def format_error(err, source, filename):
    """Render an error with the offending source line and a pointer."""
    if err.file:                    # a problem in an imported file: show that file, not the program
        try:
            with open(err.file, encoding="utf-8") as f:
                source = f.read()
            filename = os.path.basename(err.file)
        except OSError:
            pass
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
