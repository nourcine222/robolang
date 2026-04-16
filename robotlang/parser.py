from __future__ import annotations

from .ast_nodes import (
    AssignStmt,
    BinaryOp,
    Block,
    Boolean,
    BreakStmt,
    CallExpr,
    CallStmt,
    ContinueStmt,
    GotoStmt,
    IfStmt,
    IndexExpr,
    LetStmt,
    ListLiteral,
    MoveStmt,
    Number,
    PathFindExpr,
    Predicate,
    PrintStmt,
    ProcDef,
    Program,
    ReadExpr,
    RepeatStmt,
    ReturnStmt,
    SetIndexStmt,
    String,
    TurnStmt,
    RandomizeStmt,
    UnaryOp,
    VarRef,
    WaitStmt,
    WhileStmt,
    WriteStmt,
)
from .errors import ParseError
from .tokenizer import Token


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Program:
        statements = []
        while not self._check("EOF"):
            if self._match("SEMI"):
                continue
            statements.append(self._statement())
            self._match("SEMI")
        return Program(statements)

    def _statement(self):
        if self._match("LET"):
            name = self._consume("IDENT", "Expected variable name after let")
            self._consume("ASSIGN", "Expected '=' after variable name")
            expr = self._expression()
            return LetStmt(name.value, expr, name.pos)
        if self._match("MOVE"):
            tok = self._previous()
            return MoveStmt(self._expression(), tok.pos)
        if self._match("TURN"):
            tok = self._previous()
            return TurnStmt(self._expression(), tok.pos)
        if self._match("WAIT"):
            tok = self._previous()
            return WaitStmt(self._expression(), tok.pos)
        if self._match("PRINT"):
            tok = self._previous()
            return PrintStmt(self._expression(), tok.pos)
        if self._match("WRITE"):
            tok = self._previous()
            if self._match("LPAREN"):
                path = self._expression()
                self._consume("COMMA", "Expected ',' after write path")
                expr = self._expression()
                self._consume("RPAREN", "Expected ')' after write arguments")
                return WriteStmt(path, expr, tok.pos)
            path = self._expression()
            self._consume("COMMA", "Expected ',' after write path")
            expr = self._expression()
            return WriteStmt(path, expr, tok.pos)
        if self._match("GOTO"):
            tok = self._previous()
            if self._match("LPAREN"):
                x = self._expression()
                self._consume("COMMA", "Expected ',' between goto coordinates")
                y = self._expression()
                self._consume("RPAREN", "Expected ')' after goto arguments")
                return GotoStmt(x, y, tok.pos)
            x = self._expression()
            self._consume("COMMA", "Expected ',' between goto coordinates")
            y = self._expression()
            return GotoStmt(x, y, tok.pos)
        if self._match("RANDOMIZE"):
            tok = self._previous()
            if self._match("LPAREN"):
                if not self._check("RPAREN"):
                    self._argument_list()
                self._consume("RPAREN", "Expected ')' after randomize")
            return RandomizeStmt(tok.pos)
        if self._match("REPEAT"):
            tok = self._previous()
            count = self._expression()
            return RepeatStmt(count, self._block(), tok.pos)
        if self._match("WHILE"):
            tok = self._previous()
            cond = self._expression()
            return WhileStmt(cond, self._block(), tok.pos)
        if self._match("IF"):
            tok = self._previous()
            cond = self._expression()
            then_block = self._block()
            else_block = None
            if self._match("ELSE"):
                else_block = self._block()
            return IfStmt(cond, then_block, else_block, tok.pos)
        if self._match("PROC"):
            tok = self._previous()
            name = self._consume("IDENT", "Expected procedure name")
            self._consume("LPAREN", "Expected '(' after procedure name")
            params: list[str] = []
            if not self._check("RPAREN"):
                while True:
                    param = self._consume("IDENT", "Expected parameter name")
                    params.append(param.value)
                    if not self._match("COMMA"):
                        break
            self._consume("RPAREN", "Expected ')' after parameters")
            return ProcDef(name.value, params, self._block(), tok.pos)
        if self._match("RETURN"):
            tok = self._previous()
            if self._check("SEMI") or self._check("RBRACE"):
                return ReturnStmt(None, tok.pos)
            return ReturnStmt(self._expression(), tok.pos)
        if self._match("BREAK"):
            return BreakStmt(self._previous().pos)
        if self._match("CONTINUE"):
            return ContinueStmt(self._previous().pos)
        if self._check("IDENT"):
            return self._identifier_statement()
        tok = self._peek()
        raise ParseError(f"Unexpected token {tok.type}", tok.pos.line, tok.pos.column, tok.line_text)

    def _identifier_statement(self):
        name = self._advance()
        if self._match("ASSIGN"):
            return AssignStmt(name.value, self._expression(), name.pos)
        if self._match("LPAREN"):
            args = self._argument_list()
            return CallStmt(name.value, args, name.pos)
        if self._match("LBRACKET"):
            index = self._expression()
            self._consume("RBRACKET", "Expected ']' after index")
            if self._match("ASSIGN"):
                value = self._expression()
                return SetIndexStmt(VarRef(name.value, name.pos), index, value, name.pos)
            raise ParseError("Expected '=' after indexed target", self._peek().pos.line, self._peek().pos.column)
        raise ParseError("Expected assignment or call after identifier", name.pos.line, name.pos.column, name.line_text)

    def _block(self) -> Block:
        self._consume("LBRACE", "Expected '{' to start a block")
        statements = []
        while not self._check("RBRACE"):
            if self._check("EOF"):
                tok = self._peek()
                raise ParseError("Unterminated block", tok.pos.line, tok.pos.column, tok.line_text)
            if self._match("SEMI"):
                continue
            statements.append(self._statement())
            self._match("SEMI")
        self._consume("RBRACE", "Expected '}' after block")
        return Block(statements)

    def _argument_list(self) -> list:
        args = []
        if not self._check("RPAREN"):
            while True:
                args.append(self._expression())
                if not self._match("COMMA"):
                    break
        self._consume("RPAREN", "Expected ')' after arguments")
        return args

    def _expression(self):
        return self._or()

    def _or(self):
        expr = self._and()
        while self._match("OR"):
            op = self._previous()
            expr = BinaryOp(expr, "or", self._and(), op.pos)
        return expr

    def _and(self):
        expr = self._equality()
        while self._match("AND"):
            op = self._previous()
            expr = BinaryOp(expr, "and", self._equality(), op.pos)
        return expr

    def _equality(self):
        expr = self._comparison()
        while self._match("EQ", "NE"):
            op = self._previous()
            expr = BinaryOp(expr, op.value, self._comparison(), op.pos)
        return expr

    def _comparison(self):
        expr = self._term()
        while self._match("LT", "LE", "GT", "GE"):
            op = self._previous()
            expr = BinaryOp(expr, op.value, self._term(), op.pos)
        return expr

    def _term(self):
        expr = self._factor()
        while self._match("PLUS", "MINUS"):
            op = self._previous()
            expr = BinaryOp(expr, op.value, self._factor(), op.pos)
        return expr

    def _factor(self):
        expr = self._unary()
        while self._match("STAR", "SLASH", "PERCENT"):
            op = self._previous()
            expr = BinaryOp(expr, op.value, self._unary(), op.pos)
        return expr

    def _unary(self):
        if self._match("MINUS", "BANG", "NOT"):
            op = self._previous()
            return UnaryOp(op.value, self._unary(), op.pos)
        return self._postfix()

    def _postfix(self):
        expr = self._primary()
        while True:
            if self._match("LPAREN"):
                args = self._argument_list()
                if isinstance(expr, VarRef):
                    expr = CallExpr(expr.name, args, expr.pos)
                else:
                    raise ParseError("Only named functions can be called", expr.pos.line, expr.pos.column)
                continue
            if self._match("LBRACKET"):
                index = self._expression()
                self._consume("RBRACKET", "Expected ']' after index")
                expr = IndexExpr(expr, index, expr.pos)
                continue
            break
        return expr

    def _primary(self):
        if self._match("NUMBER"):
            tok = self._previous()
            return Number(tok.value, tok.pos)
        if self._match("STRING"):
            tok = self._previous()
            return String(tok.value, tok.pos)
        if self._match("BOOL"):
            tok = self._previous()
            return Boolean(tok.value, tok.pos)
        if self._match("IDENT"):
            tok = self._previous()
            return VarRef(tok.value, tok.pos)
        if self._match("OBSTACLE_AHEAD", "AT_GOAL", "IN_BOUNDS"):
            tok = self._previous()
            return Predicate(tok.value.lower(), tok.pos)
        if self._match("READ"):
            tok = self._previous()
            self._consume("LPAREN", "Expected '(' after read")
            path = self._expression()
            self._consume("RPAREN", "Expected ')' after read")
            return ReadExpr(path, tok.pos)
        if self._match("PATHFIND"):
            tok = self._previous()
            self._consume("LPAREN", "Expected '(' after pathfind")
            x = self._expression()
            self._consume("COMMA", "Expected ',' after pathfind x")
            y = self._expression()
            self._consume("RPAREN", "Expected ')' after pathfind")
            return PathFindExpr(x, y, tok.pos)
        if self._match("LBRACKET"):
            items = []
            start = self._previous().pos
            if not self._check("RBRACKET"):
                while True:
                    items.append(self._expression())
                    if not self._match("COMMA"):
                        break
            self._consume("RBRACKET", "Expected ']' after list literal")
            return ListLiteral(items, start)
        if self._match("LPAREN"):
            expr = self._expression()
            self._consume("RPAREN", "Expected ')' after expression")
            return expr
        tok = self._peek()
        raise ParseError(f"Expected expression, got {tok.type}", tok.pos.line, tok.pos.column, tok.line_text)

    def _match(self, *types: str) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        tok = self._peek()
        raise ParseError(message, tok.pos.line, tok.pos.column, tok.line_text)

    def _check(self, token_type: str) -> bool:
        if self._is_at_end():
            return token_type == "EOF"
        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _is_at_end(self) -> bool:
        return self._peek().type == "EOF"
