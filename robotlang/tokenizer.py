from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Position
from .errors import LexError


@dataclass(frozen=True)
class Token:
    type: str
    value: object
    pos: Position
    line_text: str = ""


KEYWORDS = {
    "let",
    "move",
    "turn",
    "wait",
    "print",
    "write",
    "goto",
    "randomize",
    "read",
    "pathfind",
    "repeat",
    "while",
    "if",
    "else",
    "proc",
    "return",
    "break",
    "continue",
    "true",
    "false",
    "and",
    "or",
    "not",
    "obstacle_ahead",
    "at_goal",
    "in_bounds",
}


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.lines = text.splitlines()
        self.index = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while not self._eof():
            ch = self._peek()
            if ch in " \t\r":
                self._advance()
                continue
            if ch == "\n":
                self._advance_line()
                continue
            if ch == "#" or (ch == "/" and self._peek(1) == "/"):
                self._skip_comment()
                continue
            if ch == '"':
                tokens.append(self._string())
                continue
            if ch.isalpha() or ch == "_":
                tokens.append(self._identifier())
                continue
            if ch.isdigit():
                tokens.append(self._number())
                continue
            tokens.append(self._symbol())
        tokens.append(Token("EOF", None, Position(self.line, self.column, self._current_line_text()), self._current_line_text()))
        return tokens

    def _identifier(self) -> Token:
        line_text = self._current_line_text()
        start = Position(self.line, self.column, line_text)
        chars = []
        while not self._eof() and (self._peek().isalnum() or self._peek() == "_"):
            chars.append(self._advance())
        text = "".join(chars)
        token_type = text.upper() if text in KEYWORDS else "IDENT"
        value = text
        if text == "true":
            token_type = "BOOL"
            value = True
        elif text == "false":
            token_type = "BOOL"
            value = False
        return Token(token_type, value, start, line_text)

    def _number(self) -> Token:
        line_text = self._current_line_text()
        start = Position(self.line, self.column, line_text)
        chars = []
        dot_seen = False
        while not self._eof():
            ch = self._peek()
            if ch == ".":
                if dot_seen:
                    break
                dot_seen = True
                chars.append(self._advance())
            elif ch.isdigit():
                chars.append(self._advance())
            else:
                break
        text = "".join(chars)
        value = float(text) if "." in text else int(text)
        return Token("NUMBER", value, start, line_text)

    def _string(self) -> Token:
        line_text = self._current_line_text()
        start = Position(self.line, self.column, line_text)
        self._advance()  # opening quote
        chars: list[str] = []
        while not self._eof():
            ch = self._peek()
            if ch == '"':
                self._advance()
                return Token("STRING", "".join(chars), start, line_text)
            if ch == "\\":
                self._advance()
                esc = self._peek()
                if esc == "n":
                    chars.append("\n")
                elif esc == "t":
                    chars.append("\t")
                elif esc == "r":
                    chars.append("\r")
                elif esc == '"':
                    chars.append('"')
                elif esc == "\\":
                    chars.append("\\")
                else:
                    raise LexError(f"Unknown escape sequence '\\{esc}'", start.line, start.column, line_text)
                self._advance()
                continue
            if ch == "\n":
                raise LexError("Unterminated string literal", start.line, start.column, line_text)
            chars.append(self._advance())
        raise LexError("Unterminated string literal", start.line, start.column, line_text)

    def _symbol(self) -> Token:
        line_text = self._current_line_text()
        start = Position(self.line, self.column, line_text)
        ch = self._advance()
        nxt = self._peek()
        if ch == "=" and nxt == "=":
            self._advance()
            return Token("EQ", "==", start, line_text)
        if ch == "!" and nxt == "=":
            self._advance()
            return Token("NE", "!=", start, line_text)
        if ch == "<" and nxt == "=":
            self._advance()
            return Token("LE", "<=", start, line_text)
        if ch == ">" and nxt == "=":
            self._advance()
            return Token("GE", ">=", start, line_text)
        mapping = {
            "+": "PLUS",
            "-": "MINUS",
            "*": "STAR",
            "/": "SLASH",
            "%": "PERCENT",
            "=": "ASSIGN",
            "<": "LT",
            ">": "GT",
            "!": "BANG",
            "(": "LPAREN",
            ")": "RPAREN",
            "{": "LBRACE",
            "}": "RBRACE",
            "[": "LBRACKET",
            "]": "RBRACKET",
            ",": "COMMA",
            ";": "SEMI",
            ":": "COLON",
        }
        if ch not in mapping:
            raise LexError(f"Unexpected character '{ch}'", start.line, start.column, line_text)
        return Token(mapping[ch], ch, start, line_text)

    def _skip_comment(self) -> None:
        while not self._eof() and self._peek() != "\n":
            self._advance()

    def _advance(self) -> str:
        ch = self.text[self.index]
        self.index += 1
        self.column += 1
        return ch

    def _advance_line(self) -> None:
        self.index += 1
        self.line += 1
        self.column = 1

    def _peek(self, offset: int = 0) -> str:
        idx = self.index + offset
        if idx >= len(self.text):
            return "\0"
        return self.text[idx]

    def _eof(self) -> bool:
        return self.index >= len(self.text)

    def _current_line_text(self) -> str:
        if 1 <= self.line <= len(self.lines):
            return self.lines[self.line - 1]
        return ""
