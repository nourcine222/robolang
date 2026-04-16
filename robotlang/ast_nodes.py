from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Position:
    line: int
    column: int
    line_text: str = ""


@dataclass
class Program:
    statements: list[Any]


@dataclass
class Block:
    statements: list[Any]


@dataclass
class LetStmt:
    name: str
    expr: Any
    pos: Position


@dataclass
class AssignStmt:
    name: str
    expr: Any
    pos: Position


@dataclass
class SetIndexStmt:
    target: Any
    index: Any
    value: Any
    pos: Position


@dataclass
class MoveStmt:
    expr: Any
    pos: Position


@dataclass
class TurnStmt:
    expr: Any
    pos: Position


@dataclass
class WaitStmt:
    expr: Any
    pos: Position


@dataclass
class PrintStmt:
    expr: Any
    pos: Position


@dataclass
class WriteStmt:
    path: Any
    expr: Any
    pos: Position


@dataclass
class GotoStmt:
    x: Any
    y: Any
    pos: Position


@dataclass
class RandomizeStmt:
    pos: Position


@dataclass
class RepeatStmt:
    count: Any
    block: Block
    pos: Position


@dataclass
class WhileStmt:
    condition: Any
    block: Block
    pos: Position


@dataclass
class IfStmt:
    condition: Any
    then_block: Block
    else_block: Optional[Block]
    pos: Position


@dataclass
class ProcDef:
    name: str
    params: list[str]
    block: Block
    pos: Position


@dataclass
class ReturnStmt:
    expr: Any | None
    pos: Position


@dataclass
class BreakStmt:
    pos: Position


@dataclass
class ContinueStmt:
    pos: Position


@dataclass
class CallStmt:
    name: str
    args: list[Any]
    pos: Position


@dataclass
class BinaryOp:
    left: Any
    op: str
    right: Any
    pos: Position


@dataclass
class UnaryOp:
    op: str
    operand: Any
    pos: Position


@dataclass
class Number:
    value: float | int
    pos: Position


@dataclass
class Boolean:
    value: bool
    pos: Position


@dataclass
class String:
    value: str
    pos: Position


@dataclass
class VarRef:
    name: str
    pos: Position


@dataclass
class Predicate:
    name: str
    pos: Position


@dataclass
class ListLiteral:
    items: list[Any]
    pos: Position


@dataclass
class IndexExpr:
    target: Any
    index: Any
    pos: Position


@dataclass
class CallExpr:
    name: str
    args: list[Any]
    pos: Position


@dataclass
class ReadExpr:
    path: Any
    pos: Position


@dataclass
class PathFindExpr:
    x: Any
    y: Any
    pos: Position
