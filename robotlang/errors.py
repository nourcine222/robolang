from __future__ import annotations


def _format_snippet(line: int | None, column: int | None, text: str | None) -> str:
    if line is None or column is None:
        return ""
    if not text:
        return f"\n  line {line}, column {column}"
    caret = " " * max(column - 1, 0) + "^"
    return f"\n  line {line}, column {column}\n  {text}\n  {caret}"


class RobotLangError(Exception):
    """Base class for all RobotLang errors."""

    def __init__(
        self,
        message: str,
        line: int | None = None,
        column: int | None = None,
        line_text: str | None = None,
    ):
        self.message = message
        self.line = line
        self.column = column
        self.line_text = line_text
        super().__init__(f"{message}{_format_snippet(line, column, line_text)}")


class LexError(RobotLangError):
    pass


class ParseError(RobotLangError):
    pass


class SemanticError(RobotLangError):
    pass


class RuntimeRobotError(RobotLangError):
    pass
