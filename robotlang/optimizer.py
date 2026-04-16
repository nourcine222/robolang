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
    UnaryOp,
    VarRef,
    WaitStmt,
    WhileStmt,
    WriteStmt,
)


class Optimizer:
    def optimize(self, program: Program) -> Program:
        return Program([self._stmt(stmt) for stmt in program.statements])

    def _stmt(self, stmt):
        if isinstance(stmt, LetStmt):
            return LetStmt(stmt.name, self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, AssignStmt):
            return AssignStmt(stmt.name, self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, SetIndexStmt):
            return SetIndexStmt(self._expr(stmt.target), self._expr(stmt.index), self._expr(stmt.value), stmt.pos)
        if isinstance(stmt, MoveStmt):
            return MoveStmt(self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, TurnStmt):
            return TurnStmt(self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, WaitStmt):
            return WaitStmt(self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, PrintStmt):
            return PrintStmt(self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, WriteStmt):
            return WriteStmt(self._expr(stmt.path), self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, GotoStmt):
            return GotoStmt(self._expr(stmt.x), self._expr(stmt.y), stmt.pos)
        if isinstance(stmt, RepeatStmt):
            return RepeatStmt(self._expr(stmt.count), Block([self._stmt(s) for s in stmt.block.statements]), stmt.pos)
        if isinstance(stmt, WhileStmt):
            return WhileStmt(self._expr(stmt.condition), Block([self._stmt(s) for s in stmt.block.statements]), stmt.pos)
        if isinstance(stmt, IfStmt):
            else_block = None if stmt.else_block is None else Block([self._stmt(s) for s in stmt.else_block.statements])
            return IfStmt(self._expr(stmt.condition), Block([self._stmt(s) for s in stmt.then_block.statements]), else_block, stmt.pos)
        if isinstance(stmt, ProcDef):
            return ProcDef(stmt.name, stmt.params, Block([self._stmt(s) for s in stmt.block.statements]), stmt.pos)
        if isinstance(stmt, ReturnStmt):
            return ReturnStmt(None if stmt.expr is None else self._expr(stmt.expr), stmt.pos)
        if isinstance(stmt, (BreakStmt, ContinueStmt, CallStmt)):
            if isinstance(stmt, CallStmt):
                return CallStmt(stmt.name, [self._expr(arg) for arg in stmt.args], stmt.pos)
            return stmt
        return stmt

    def _expr(self, expr):
        if isinstance(expr, (Number, Boolean, String, VarRef, Predicate)):
            return expr
        if isinstance(expr, ListLiteral):
            return ListLiteral([self._expr(item) for item in expr.items], expr.pos)
        if isinstance(expr, IndexExpr):
            return IndexExpr(self._expr(expr.target), self._expr(expr.index), expr.pos)
        if isinstance(expr, CallExpr):
            return CallExpr(expr.name, [self._expr(arg) for arg in expr.args], expr.pos)
        if isinstance(expr, (ReadExpr, PathFindExpr)):
            if isinstance(expr, ReadExpr):
                return ReadExpr(self._expr(expr.path), expr.pos)
            return PathFindExpr(self._expr(expr.x), self._expr(expr.y), expr.pos)
        if isinstance(expr, UnaryOp):
            operand = self._expr(expr.operand)
            folded = self._fold_unary(expr.op, operand, expr.pos)
            return folded if folded is not None else UnaryOp(expr.op, operand, expr.pos)
        if isinstance(expr, BinaryOp):
            left = self._expr(expr.left)
            right = self._expr(expr.right)
            folded = self._fold_binary(expr.op, left, right, expr.pos)
            return folded if folded is not None else BinaryOp(left, expr.op, right, expr.pos)
        return expr

    def _fold_unary(self, op: str, operand, pos):
        if isinstance(operand, Number) and op == "-":
            return Number(-operand.value, pos)
        if isinstance(operand, Boolean) and op in ("!", "not"):
            return Boolean(not operand.value, pos)
        return None

    def _fold_binary(self, op: str, left, right, pos):
        if isinstance(left, Number) and isinstance(right, Number):
            if op == "+":
                return Number(left.value + right.value, pos)
            if op == "-":
                return Number(left.value - right.value, pos)
            if op == "*":
                return Number(left.value * right.value, pos)
            if op == "/" and right.value != 0:
                return Number(left.value / right.value, pos)
            if op == "%":
                return Number(left.value % right.value, pos)
            if op == "==":
                return Boolean(left.value == right.value, pos)
            if op == "!=":
                return Boolean(left.value != right.value, pos)
            if op == "<":
                return Boolean(left.value < right.value, pos)
            if op == "<=":
                return Boolean(left.value <= right.value, pos)
            if op == ">":
                return Boolean(left.value > right.value, pos)
            if op == ">=":
                return Boolean(left.value >= right.value, pos)
        if isinstance(left, Boolean) and isinstance(right, Boolean):
            if op == "and":
                return Boolean(left.value and right.value, pos)
            if op == "or":
                return Boolean(left.value or right.value, pos)
            if op == "==":
                return Boolean(left.value == right.value, pos)
            if op == "!=":
                return Boolean(left.value != right.value, pos)
        return None
