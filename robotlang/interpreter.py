from __future__ import annotations

from .analyzer import Analyzer
from .bytecode import BytecodeProgram
from .compiler import Compiler
from .optimizer import Optimizer
from .ast_nodes import Program
from .vm import VM
from .world import RobotState, World


class Interpreter:
    def __init__(self, world: World | None = None, robot: RobotState | None = None, trace: bool = False, on_event=None):
        self.world = world or World(8, 8, obstacles={(7, 7)}, goal=(6, 6))
        self.robot = robot or RobotState(0, 0, "east")
        self.trace = trace
        self.on_event = on_event
        self.output: list[str] = []
        self.bytecode: BytecodeProgram | None = None
        self.analyzer = Analyzer()
        self.optimizer = Optimizer()
        self.compiler = Compiler()

    def run(self, program: Program) -> list[str]:
        self.analyzer.analyze(program)
        optimized = self.optimizer.optimize(program)
        compiled = self.compiler.compile(optimized)
        self.bytecode = compiled
        vm = VM(self.world, self.robot, trace=self.trace, on_event=self.on_event)
        self.output = vm.run(compiled)
        return self.output
