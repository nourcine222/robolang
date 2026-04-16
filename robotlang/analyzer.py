from __future__ import annotations

from dataclasses import dataclass, field

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
from .errors import SemanticError


BUILTIN_PREDICATES = {"obstacle_ahead", "at_goal", "in_bounds"}
BUILTIN_CALLS = {"read": 1, "pathfind": 2}


@dataclass
class Scope:
    parent: "Scope | None" = None
    vars: set[str] = field(default_factory=set)
    procs: dict[str, ProcDef] = field(default_factory=dict)

    def define_var(self, name: str) -> None:
        self.vars.add(name)

    def define_proc(self, proc: ProcDef) -> None:
        self.procs[proc.name] = proc

    def resolve_var(self, name: str) -> bool:
        if name in self.vars:
            return True
        if self.parent is not None:
            return self.parent.resolve_var(name)
        return False

    def resolve_proc(self, name: str) -> bool:
        if name in self.procs:
            return True
        if self.parent is not None:
            return self.parent.resolve_proc(name)
        return False

    def resolve_proc_def(self, name: str) -> ProcDef | None:
        if name in self.procs:
            return self.procs[name]
        if self.parent is not None:
            return self.parent.resolve_proc_def(name)
        return None


class Analyzer:
    def __init__(self) -> None:
        self.global_scope = Scope()

    def analyze(self, program: Program) -> None:
        self._block(program.statements, self.global_scope, loop_depth=0, func_depth=0)

    def _predeclare_procs(self, statements, scope: Scope) -> None:
        for stmt in statements:
            if isinstance(stmt, ProcDef):
                if stmt.name in scope.procs:
                    raise SemanticError(f"Procedure '{stmt.name}' already defined", stmt.pos.line, stmt.pos.column, None)
                scope.define_proc(stmt)

    def _block(self, statements, scope: Scope, loop_depth: int, func_depth: int) -> None:
        self._predeclare_procs(statements, scope)
        for stmt in statements:
            self._statement(stmt, scope, loop_depth, func_depth)

    def _statement(self, stmt, scope: Scope, loop_depth: int, func_depth: int) -> None:
        if isinstance(stmt, LetStmt):
            self._expr(stmt.expr, scope, func_depth)
            if scope.resolve_proc(stmt.name):
                raise SemanticError(f"'{stmt.name}' is reserved for a procedure name", stmt.pos.line, stmt.pos.column, None)
            if stmt.name in scope.vars:
                raise SemanticError(f"Variable '{stmt.name}' already declared in this scope", stmt.pos.line, stmt.pos.column, None)
            scope.define_var(stmt.name)
        elif isinstance(stmt, AssignStmt):
            self._expr(stmt.expr, scope, func_depth)
            if not scope.resolve_var(stmt.name):
                raise SemanticError(f"Variable '{stmt.name}' used before declaration", stmt.pos.line, stmt.pos.column, None)
        elif isinstance(stmt, SetIndexStmt):
            self._expr(stmt.target, scope, func_depth)
            self._expr(stmt.index, scope, func_depth)
            self._expr(stmt.value, scope, func_depth)
        elif isinstance(stmt, MoveStmt):
            self._expr(stmt.expr, scope, func_depth)
        elif isinstance(stmt, TurnStmt):
            self._expr(stmt.expr, scope, func_depth)
        elif isinstance(stmt, WaitStmt):
            self._expr(stmt.expr, scope, func_depth)
        elif isinstance(stmt, PrintStmt):
            self._expr(stmt.expr, scope, func_depth)
        elif isinstance(stmt, WriteStmt):
            self._expr(stmt.path, scope, func_depth)
            self._expr(stmt.expr, scope, func_depth)
        elif isinstance(stmt, GotoStmt):
            self._expr(stmt.x, scope, func_depth)
            self._expr(stmt.y, scope, func_depth)
        elif isinstance(stmt, RandomizeStmt):
            return
        elif isinstance(stmt, RepeatStmt):
            self._expr(stmt.count, scope, func_depth)
            self._block(stmt.block.statements, Scope(scope), loop_depth + 1, func_depth)
        elif isinstance(stmt, WhileStmt):
            self._expr(stmt.condition, scope, func_depth)
            self._block(stmt.block.statements, Scope(scope), loop_depth + 1, func_depth)
        elif isinstance(stmt, IfStmt):
            self._expr(stmt.condition, scope, func_depth)
            self._block(stmt.then_block.statements, Scope(scope), loop_depth, func_depth)
            if stmt.else_block is not None:
                self._block(stmt.else_block.statements, Scope(scope), loop_depth, func_depth)
        elif isinstance(stmt, ProcDef):
            local = Scope(scope)
            for param in stmt.params:
                if param in local.vars:
                    raise SemanticError(f"Duplicate parameter '{param}'", stmt.pos.line, stmt.pos.column, None)
                local.define_var(param)
            self._block(stmt.block.statements, local, loop_depth=0, func_depth=func_depth + 1)
        elif isinstance(stmt, ReturnStmt):
            if func_depth <= 0:
                raise SemanticError("return is only valid inside a procedure", stmt.pos.line, stmt.pos.column, None)
            if stmt.expr is not None:
                self._expr(stmt.expr, scope, func_depth)
        elif isinstance(stmt, BreakStmt):
            if loop_depth <= 0:
                raise SemanticError("break is only valid inside a loop", stmt.pos.line, stmt.pos.column, None)
        elif isinstance(stmt, ContinueStmt):
            if loop_depth <= 0:
                raise SemanticError("continue is only valid inside a loop", stmt.pos.line, stmt.pos.column, None)
        elif isinstance(stmt, CallStmt):
            self._call(stmt.name, stmt.args, stmt.pos, scope, func_depth)
        else:
            raise SemanticError(f"Unsupported statement type: {type(stmt).__name__}")

    def _call(self, name: str, args, pos, scope: Scope, func_depth: int) -> None:
        proc = scope.resolve_proc_def(name)
        if proc is None and name not in BUILTIN_CALLS:
            raise SemanticError(f"Unknown procedure '{name}'", pos.line, pos.column, None)
        if proc is not None and len(args) != len(proc.params):
            raise SemanticError(
                f"Procedure '{name}' expects {len(proc.params)} arguments but got {len(args)}",
                pos.line,
                pos.column,
                None,
            )
        if proc is None and len(args) != BUILTIN_CALLS[name]:
            raise SemanticError(
                f"Builtin '{name}' expects {BUILTIN_CALLS[name]} arguments but got {len(args)}",
                pos.line,
                pos.column,
                None,
            )
        for arg in args:
            self._expr(arg, scope, func_depth)

    def _expr(self, expr, scope: Scope, func_depth: int) -> None:
        if isinstance(expr, (Number, Boolean, String)):
            return
        if isinstance(expr, VarRef):
            if not scope.resolve_var(expr.name):
                raise SemanticError(f"Variable '{expr.name}' used before declaration", expr.pos.line, expr.pos.column, expr.pos.line_text)
            return
        if isinstance(expr, Predicate):
            if expr.name not in BUILTIN_PREDICATES:
                raise SemanticError(f"Unknown predicate '{expr.name}'", expr.pos.line, expr.pos.column, expr.pos.line_text)
            return
        if isinstance(expr, UnaryOp):
            self._expr(expr.operand, scope, func_depth)
            return
        if isinstance(expr, BinaryOp):
            self._expr(expr.left, scope, func_depth)
            self._expr(expr.right, scope, func_depth)
            return
        if isinstance(expr, ListLiteral):
            for item in expr.items:
                self._expr(item, scope, func_depth)
            return
        if isinstance(expr, IndexExpr):
            self._expr(expr.target, scope, func_depth)
            self._expr(expr.index, scope, func_depth)
            return
        if isinstance(expr, CallExpr):
            self._call(expr.name, expr.args, expr.pos, scope, func_depth)
            return
        if isinstance(expr, ReadExpr):
            self._expr(expr.path, scope, func_depth)
            return
        if isinstance(expr, PathFindExpr):
            self._expr(expr.x, scope, func_depth)
            self._expr(expr.y, scope, func_depth)
            return
        raise SemanticError(f"Unsupported expression type: {type(expr).__name__}")
