from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ast_nodes import Position
from .bytecode import BytecodeProgram, FunctionCode, Instruction
from .errors import RuntimeRobotError
from .world import RobotState, World


@dataclass
class ProcValue:
    code: FunctionCode
    closure: "Frame"


@dataclass
class Frame:
    vars: dict[str, object] = field(default_factory=dict)
    procs: dict[str, ProcValue] = field(default_factory=dict)
    parent: "Frame | None" = None

    def define_var(self, name: str, value: object) -> None:
        self.vars[name] = value

    def set_var(self, name: str, value: object) -> None:
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent is not None:
            self.parent.set_var(name, value)
            return
        raise RuntimeRobotError(f"Unknown variable '{name}'")

    def get_var(self, name: str) -> object:
        if name in self.vars:
            return self.vars[name]
        if self.parent is not None:
            return self.parent.get_var(name)
        raise RuntimeRobotError(f"Unknown variable '{name}'")

    def define_proc(self, name: str, value: ProcValue) -> None:
        self.procs[name] = value

    def get_proc(self, name: str) -> ProcValue:
        if name in self.procs:
            return self.procs[name]
        if self.parent is not None:
            return self.parent.get_proc(name)
        raise RuntimeRobotError(f"Unknown procedure '{name}'")


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class VM:
    def __init__(
        self,
        world: World | None = None,
        robot: RobotState | None = None,
        trace: bool = False,
        on_event=None,
    ) -> None:
        self.world = world or World(8, 8, obstacles={(7, 7)}, goal=(6, 6))
        self.robot = robot or RobotState(0, 0, "east")
        self.trace = trace
        self.on_event = on_event
        self.output: list[str] = []

    def run(self, program: BytecodeProgram) -> list[str]:
        frame = Frame()
        self._exec(program.instructions, frame)
        return self.output

    def _exec(self, instructions: list[Instruction], frame: Frame):
        labels = {instr.args[0]: idx for idx, instr in enumerate(instructions) if instr.op == "LABEL"}
        pc = 0
        stack: list[object] = []
        scope_depth = 0
        while pc < len(instructions):
            instr = instructions[pc]
            op = instr.op
            if op == "LABEL":
                pc += 1
                continue
            if op == "ENTER_SCOPE":
                frame = Frame(parent=frame)
                scope_depth += 1
                pc += 1
                continue
            elif op == "EXIT_SCOPE":
                if frame.parent is None:
                    raise RuntimeRobotError("Cannot exit global scope")
                frame = frame.parent
                scope_depth -= 1
                pc += 1
                continue
            if op == "PUSH_CONST":
                stack.append(instr.args[0])
            elif op == "DECLARE":
                frame.define_var(instr.args[0], stack.pop())
            elif op == "LOAD":
                stack.append(frame.get_var(instr.args[0]))
            elif op == "STORE":
                value = stack.pop()
                frame.set_var(instr.args[0], value)
            elif op == "POP":
                stack.pop()
            elif op == "BUILD_LIST":
                n = instr.args[0]
                items = stack[-n:] if n else []
                if n:
                    del stack[-n:]
                stack.append(list(items))
            elif op == "INDEX_GET":
                index = self._to_int(stack.pop(), instr.pos)
                target = stack.pop()
                stack.append(self._index_get(target, index, instr.pos))
            elif op == "INDEX_SET":
                value = stack.pop()
                index = self._to_int(stack.pop(), instr.pos)
                target = stack.pop()
                self._index_set(target, index, value, instr.pos)
            elif op == "UNARY":
                operand = stack.pop()
                stack.append(self._unary(instr.args[0], operand, instr.pos))
            elif op == "BINARY":
                right = stack.pop()
                left = stack.pop()
                stack.append(self._binary(instr.args[0], left, right, instr.pos))
            elif op == "JUMP":
                pc = labels[instr.args[0]]
                continue
            elif op == "JUMP_IF_FALSE":
                value = self._truthy(stack.pop())
                if not value:
                    pc = labels[instr.args[0]]
                    continue
            elif op == "JUMP_IF_TRUE":
                value = self._truthy(stack.pop())
                if value:
                    pc = labels[instr.args[0]]
                    continue
            elif op == "BREAK":
                label, target_depth = instr.args
                frame, scope_depth = self._unwind_scopes(frame, scope_depth, target_depth)
                pc = labels[label]
                continue
            elif op == "CONTINUE":
                label, target_depth = instr.args
                frame, scope_depth = self._unwind_scopes(frame, scope_depth, target_depth)
                pc = labels[label]
                continue
            elif op == "DEF_PROC":
                name, code = instr.args
                frame.define_proc(name, ProcValue(code, frame))
            elif op == "CALL":
                name, argc = instr.args
                args = [stack.pop() for _ in range(argc)][::-1]
                result = self._call(name, args, frame, instr.pos)
                stack.append(result)
            elif op == "RETURN":
                value = stack.pop() if stack else None
                raise ReturnSignal(value)
            elif op == "MOVE":
                self.world.move(self.robot, self._to_int(stack.pop(), instr.pos))
                self._trace_step("move")
            elif op == "TURN":
                self.robot.turn(self._to_int(stack.pop(), instr.pos))
                self._trace_step("turn")
            elif op == "WAIT":
                self._to_int(stack.pop(), instr.pos)
                self._trace_step("wait")
            elif op == "PRINT":
                value = stack.pop()
                text = self._format(value)
                self.output.append(text)
                print(text)
                self._event("print", text)
            elif op == "WRITE_FILE":
                value = stack.pop()
                path = Path(str(stack.pop()))
                path.write_text(self._format(value), encoding="utf-8")
                self._event("write", str(path))
            elif op == "READ_FILE":
                path = Path(str(stack.pop()))
                stack.append(path.read_text(encoding="utf-8"))
            elif op == "PATHFIND":
                y = self._to_int(stack.pop(), instr.pos)
                x = self._to_int(stack.pop(), instr.pos)
                path = self.world.find_path((self.robot.x, self.robot.y), (x, y))
                stack.append(path if path is not None else [])
            elif op == "GOTO":
                y = self._to_int(stack.pop(), instr.pos)
                x = self._to_int(stack.pop(), instr.pos)
                self.world.goto(self.robot, x, y)
                self._trace_step("goto")
            elif op == "RANDOMIZE":
                self.world.randomize(self.robot)
                self._trace_step("randomize")
            elif op == "PREDICATE":
                stack.append(self._predicate(instr.args[0]))
            else:
                raise RuntimeRobotError(f"Unknown instruction '{op}'")
            pc += 1
        return stack[-1] if stack else None

    def _unwind_scopes(self, frame: Frame, scope_depth: int, target_depth: int) -> tuple[Frame, int]:
        while scope_depth > target_depth:
            if frame.parent is None:
                raise RuntimeRobotError("Cannot unwind past global scope")
            frame = frame.parent
            scope_depth -= 1
        return frame, scope_depth

    def _call(self, name: str, args: list[object], frame: Frame, pos: Position | None):
        if name == "read":
            return Path(str(args[0])).read_text(encoding="utf-8")
        if name == "pathfind":
            target = (self._to_int(args[0], pos), self._to_int(args[1], pos))
            path = self.world.find_path((self.robot.x, self.robot.y), target)
            return path if path is not None else []
        proc = frame.get_proc(name)
        local = Frame(parent=proc.closure)
        for param, value in zip(proc.code.params, args):
            local.define_var(param, value)
        try:
            return self._exec(proc.code.instructions, local)
        except ReturnSignal as signal:
            return signal.value

    def _predicate(self, name: str):
        if name == "obstacle_ahead":
            return self.world.obstacle_ahead(self.robot)
        if name == "at_goal":
            return self.world.is_goal(self.robot.x, self.robot.y)
        if name == "in_bounds":
            return self.world.in_bounds(self.robot.x, self.robot.y)
        raise RuntimeRobotError(f"Unknown predicate '{name}'")

    def _index_get(self, target, index: int, pos: Position | None):
        try:
            return target[index]
        except Exception as exc:
            raise RuntimeRobotError(f"Cannot index value: {exc}", pos.line if pos else None, pos.column if pos else None) from exc

    def _index_set(self, target, index: int, value, pos: Position | None):
        try:
            target[index] = value
        except Exception as exc:
            raise RuntimeRobotError(f"Cannot assign indexed value: {exc}", pos.line if pos else None, pos.column if pos else None) from exc

    def _unary(self, op: str, value, pos: Position | None):
        if op == "-":
            return -self._number(value, pos)
        if op in ("!", "not"):
            return not self._truthy(value)
        raise RuntimeRobotError(f"Unknown unary operator '{op}'", pos.line if pos else None, pos.column if pos else None)

    def _binary(self, op: str, left, right, pos: Position | None):
        if op == "and":
            return self._truthy(left) and self._truthy(right)
        if op == "or":
            return self._truthy(left) or self._truthy(right)
        if op == "+":
            return self._number(left, pos) + self._number(right, pos)
        if op == "-":
            return self._number(left, pos) - self._number(right, pos)
        if op == "*":
            return self._number(left, pos) * self._number(right, pos)
        if op == "/":
            return self._number(left, pos) / self._number(right, pos)
        if op == "%":
            return self._number(left, pos) % self._number(right, pos)
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        raise RuntimeRobotError(f"Unknown operator '{op}'", pos.line if pos else None, pos.column if pos else None)

    def _number(self, value, pos: Position | None) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeRobotError("Expected numeric value", pos.line if pos else None, pos.column if pos else None)
        return float(value)

    def _to_int(self, value, pos: Position | None) -> int:
        number = self._number(value, pos)
        if int(number) != number:
            raise RuntimeRobotError("Expected integer value", pos.line if pos else None, pos.column if pos else None)
        return int(number)

    def _truthy(self, value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    def _format(self, value) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _trace_step(self, action: str) -> None:
        self._event("step", action)
        if self.trace:
            print(self.world.render(self.robot))

    def _event(self, kind: str, payload: str) -> None:
        if self.on_event is not None:
            self.on_event(
                {
                    "kind": kind,
                    "payload": payload,
                    "world": self.world.render(self.robot),
                    "robot": (self.robot.x, self.robot.y, self.robot.direction),
                }
            )
