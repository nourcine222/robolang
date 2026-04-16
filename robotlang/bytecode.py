from __future__ import annotations

from dataclasses import dataclass, field

from .ast_nodes import Position


@dataclass(frozen=True)
class Instruction:
    op: str
    args: tuple[object, ...] = ()
    pos: Position | None = None


@dataclass
class FunctionCode:
    name: str
    params: list[str]
    instructions: list[Instruction] = field(default_factory=list)


@dataclass
class BytecodeProgram:
    instructions: list[Instruction] = field(default_factory=list)

