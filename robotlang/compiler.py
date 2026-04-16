from __future__ import annotations

from dataclasses import dataclass

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
from .bytecode import BytecodeProgram, FunctionCode, Instruction


@dataclass
class LoopContext:
    continue_label: str
    break_label: str
    target_depth: int


class Compiler:
    def __init__(self) -> None:
        self.label_counter = 0
        self.temp_counter = 0

    def compile(self, program: Program) -> BytecodeProgram:
        code = BytecodeProgram()
        self._block(program.statements, code.instructions, loop_stack=[], scoped=False, scope_depth=0)
        return code

    def compile_function(self, proc: ProcDef) -> FunctionCode:
        code = FunctionCode(proc.name, proc.params)
        self._block(proc.block.statements, code.instructions, loop_stack=[], in_function=True, scoped=True, scope_depth=0)
        code.instructions.append(Instruction("PUSH_CONST", (None,), proc.pos))
        code.instructions.append(Instruction("RETURN", (), proc.pos))
        return code

    def _block(
        self,
        statements,
        out: list[Instruction],
        loop_stack: list[LoopContext],
        in_function: bool = False,
        scoped: bool = True,
        scope_depth: int = 0,
    ) -> int:
        if scoped:
            out.append(Instruction("ENTER_SCOPE", (), statements[0].pos if statements else None))
            scope_depth += 1
        for stmt in statements:
            self._stmt(stmt, out, loop_stack, in_function, scope_depth)
        if scoped:
            out.append(Instruction("EXIT_SCOPE", (), statements[-1].pos if statements else None))
            scope_depth -= 1
        return scope_depth

    def _stmt(self, stmt, out: list[Instruction], loop_stack: list[LoopContext], in_function: bool, scope_depth: int) -> None:
        if isinstance(stmt, LetStmt):
            self._expr(stmt.expr, out)
            out.append(Instruction("DECLARE", (stmt.name,), stmt.pos))
        elif isinstance(stmt, AssignStmt):
            self._expr(stmt.expr, out)
            out.append(Instruction("STORE", (stmt.name,), stmt.pos))
        elif isinstance(stmt, SetIndexStmt):
            self._expr(stmt.target, out)
            self._expr(stmt.index, out)
            self._expr(stmt.value, out)
            out.append(Instruction("INDEX_SET", (), stmt.pos))
        elif isinstance(stmt, MoveStmt):
            self._expr(stmt.expr, out)
            out.append(Instruction("MOVE", (), stmt.pos))
        elif isinstance(stmt, TurnStmt):
            self._expr(stmt.expr, out)
            out.append(Instruction("TURN", (), stmt.pos))
        elif isinstance(stmt, WaitStmt):
            self._expr(stmt.expr, out)
            out.append(Instruction("WAIT", (), stmt.pos))
        elif isinstance(stmt, PrintStmt):
            self._expr(stmt.expr, out)
            out.append(Instruction("PRINT", (), stmt.pos))
        elif isinstance(stmt, WriteStmt):
            self._expr(stmt.path, out)
            self._expr(stmt.expr, out)
            out.append(Instruction("WRITE_FILE", (), stmt.pos))
        elif isinstance(stmt, GotoStmt):
            self._expr(stmt.x, out)
            self._expr(stmt.y, out)
            out.append(Instruction("GOTO", (), stmt.pos))
        elif isinstance(stmt, RandomizeStmt):
            out.append(Instruction("RANDOMIZE", (), stmt.pos))
        elif isinstance(stmt, RepeatStmt):
            self._repeat(stmt, out, loop_stack, in_function, scope_depth)
        elif isinstance(stmt, WhileStmt):
            self._while(stmt, out, loop_stack, in_function, scope_depth)
        elif isinstance(stmt, IfStmt):
            self._if(stmt, out, loop_stack, in_function, scope_depth)
        elif isinstance(stmt, ProcDef):
            fn = self.compile_function(stmt)
            out.append(Instruction("DEF_PROC", (stmt.name, fn), stmt.pos))
        elif isinstance(stmt, ReturnStmt):
            if stmt.expr is None:
                out.append(Instruction("PUSH_CONST", (None,), stmt.pos))
            else:
                self._expr(stmt.expr, out)
            out.append(Instruction("RETURN", (), stmt.pos))
        elif isinstance(stmt, BreakStmt):
            if not loop_stack:
                raise ValueError("break outside loop")
            ctx = loop_stack[-1]
            out.append(Instruction("BREAK", (ctx.break_label, ctx.target_depth), stmt.pos))
        elif isinstance(stmt, ContinueStmt):
            if not loop_stack:
                raise ValueError("continue outside loop")
            ctx = loop_stack[-1]
            out.append(Instruction("CONTINUE", (ctx.continue_label, ctx.target_depth), stmt.pos))
        elif isinstance(stmt, CallStmt):
            for arg in stmt.args:
                self._expr(arg, out)
            out.append(Instruction("CALL", (stmt.name, len(stmt.args)), stmt.pos))
            out.append(Instruction("POP", (), stmt.pos))
        else:
            raise ValueError(f"Unsupported statement {type(stmt).__name__}")

    def _repeat(self, stmt: RepeatStmt, out: list[Instruction], loop_stack: list[LoopContext], in_function: bool, scope_depth: int) -> None:
        temp = self._temp()
        start = self._label("repeat_start")
        end = self._label("repeat_end")
        cont = self._label("repeat_continue")
        self._expr(stmt.count, out)
        out.append(Instruction("DECLARE", (temp,), stmt.pos))
        out.append(Instruction("LABEL", (start,), stmt.pos))
        out.append(Instruction("LOAD", (temp,), stmt.pos))
        out.append(Instruction("PUSH_CONST", (0,), stmt.pos))
        out.append(Instruction("BINARY", ("<=",), stmt.pos))
        out.append(Instruction("JUMP_IF_TRUE", (end,), stmt.pos))
        loop_stack.append(LoopContext(continue_label=cont, break_label=end, target_depth=scope_depth))
        out.append(Instruction("ENTER_SCOPE", (), stmt.pos))
        self._block(stmt.block.statements, out, loop_stack, in_function, scoped=False, scope_depth=scope_depth + 1)
        loop_stack.pop()
        out.append(Instruction("EXIT_SCOPE", (), stmt.pos))
        out.append(Instruction("LABEL", (cont,), stmt.pos))
        out.append(Instruction("LOAD", (temp,), stmt.pos))
        out.append(Instruction("PUSH_CONST", (1,), stmt.pos))
        out.append(Instruction("BINARY", ("-",), stmt.pos))
        out.append(Instruction("STORE", (temp,), stmt.pos))
        out.append(Instruction("JUMP", (start,), stmt.pos))
        out.append(Instruction("LABEL", (end,), stmt.pos))

    def _while(self, stmt: WhileStmt, out: list[Instruction], loop_stack: list[LoopContext], in_function: bool, scope_depth: int) -> None:
        start = self._label("while_start")
        end = self._label("while_end")
        out.append(Instruction("LABEL", (start,), stmt.pos))
        self._expr(stmt.condition, out)
        out.append(Instruction("JUMP_IF_FALSE", (end,), stmt.pos))
        loop_stack.append(LoopContext(continue_label=start, break_label=end, target_depth=scope_depth))
        out.append(Instruction("ENTER_SCOPE", (), stmt.pos))
        self._block(stmt.block.statements, out, loop_stack, in_function, scoped=False, scope_depth=scope_depth + 1)
        loop_stack.pop()
        out.append(Instruction("EXIT_SCOPE", (), stmt.pos))
        out.append(Instruction("JUMP", (start,), stmt.pos))
        out.append(Instruction("LABEL", (end,), stmt.pos))

    def _if(self, stmt: IfStmt, out: list[Instruction], loop_stack: list[LoopContext], in_function: bool, scope_depth: int) -> None:
        else_label = self._label("if_else")
        end_label = self._label("if_end")
        self._expr(stmt.condition, out)
        out.append(Instruction("JUMP_IF_FALSE", (else_label,), stmt.pos))
        self._block(stmt.then_block.statements, out, loop_stack, in_function, scoped=True, scope_depth=scope_depth)
        out.append(Instruction("JUMP", (end_label,), stmt.pos))
        out.append(Instruction("LABEL", (else_label,), stmt.pos))
        if stmt.else_block is not None:
            self._block(stmt.else_block.statements, out, loop_stack, in_function, scoped=True, scope_depth=scope_depth)
        out.append(Instruction("LABEL", (end_label,), stmt.pos))

    def _expr(self, expr, out: list[Instruction]) -> None:
        if isinstance(expr, (Number, Boolean, String)):
            out.append(Instruction("PUSH_CONST", (expr.value,), expr.pos))
        elif isinstance(expr, VarRef):
            out.append(Instruction("LOAD", (expr.name,), expr.pos))
        elif isinstance(expr, Predicate):
            out.append(Instruction("PREDICATE", (expr.name,), expr.pos))
        elif isinstance(expr, UnaryOp):
            self._expr(expr.operand, out)
            out.append(Instruction("UNARY", (expr.op,), expr.pos))
        elif isinstance(expr, BinaryOp):
            self._expr(expr.left, out)
            self._expr(expr.right, out)
            out.append(Instruction("BINARY", (expr.op,), expr.pos))
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self._expr(item, out)
            out.append(Instruction("BUILD_LIST", (len(expr.items),), expr.pos))
        elif isinstance(expr, IndexExpr):
            self._expr(expr.target, out)
            self._expr(expr.index, out)
            out.append(Instruction("INDEX_GET", (), expr.pos))
        elif isinstance(expr, CallExpr):
            for arg in expr.args:
                self._expr(arg, out)
            out.append(Instruction("CALL", (expr.name, len(expr.args)), expr.pos))
        elif isinstance(expr, ReadExpr):
            self._expr(expr.path, out)
            out.append(Instruction("READ_FILE", (), expr.pos))
        elif isinstance(expr, PathFindExpr):
            self._expr(expr.x, out)
            self._expr(expr.y, out)
            out.append(Instruction("PATHFIND", (), expr.pos))
        else:
            raise ValueError(f"Unsupported expression {type(expr).__name__}")

    def _label(self, prefix: str) -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def _temp(self) -> str:
        self.temp_counter += 1
        return f"__tmp_{self.temp_counter}"
