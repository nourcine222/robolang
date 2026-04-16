from __future__ import annotations

import argparse
from pathlib import Path

from .ast_printer import dump_ast
from .interpreter import Interpreter
from .parser import Parser
from .tokenizer import Lexer
from .world import RobotState, World
from .gui import RobotLangGUI


DEMO_PROGRAM = """\
let step = 1;
let path = [1, 2, 3];

proc turn_around() {
  turn 90;
  turn 90;
}

proc walk_square(n) {
  let i = 0;
  while i < n {
    move step;
    i = i + 1;
  }
  return n;
}

walk_square(2);
turn_around();

if obstacle_ahead {
  goto(0, 1);
}

goto(6, 6);
print at_goal;
"""


def parse_point(text: str) -> tuple[int, int]:
    x_str, y_str = text.split(",", 1)
    return int(x_str.strip()), int(y_str.strip())


def parse_obstacles(items: list[str]) -> set[tuple[int, int]]:
    obstacles = set()
    for item in items:
        x, y = parse_point(item)
        obstacles.add((x, y))
    return obstacles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RobotLang virtual robot compiler/interpreter")
    parser.add_argument("file", nargs="?", help="Source file to run")
    parser.add_argument("--trace", action="store_true", help="Print the world after each action")
    parser.add_argument("--ast", action="store_true", help="Print the parsed AST and exit")
    parser.add_argument("--tokens", action="store_true", help="Print the token stream and exit")
    parser.add_argument("--gui", action="store_true", help="Open the graphical robot simulator")
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--start", default="0,0,east", help="Robot start as x,y,direction")
    parser.add_argument("--goal", default="6,6", help="Goal as x,y")
    parser.add_argument("--obstacle", action="append", default=[], help="Obstacle position as x,y. Can be repeated.")
    parser.add_argument("--demo", action="store_true", help="Run the built-in demo program")
    return parser


def load_source(args: argparse.Namespace) -> str:
    if args.demo or not args.file:
        return DEMO_PROGRAM
    return Path(args.file).read_text(encoding="utf-8")


def build_world(args: argparse.Namespace) -> tuple[World, RobotState]:
    start_parts = [part.strip() for part in args.start.split(",")]
    if len(start_parts) != 3:
        raise SystemExit("--start must look like x,y,direction")
    robot = RobotState(int(start_parts[0]), int(start_parts[1]), start_parts[2].lower())
    goal = parse_point(args.goal)
    world = World(args.width, args.height, obstacles=parse_obstacles(args.obstacle), goal=goal)
    return world, robot


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = load_source(args)

    if args.tokens or args.ast:
        tokens = Lexer(source).tokenize()
        if args.tokens:
            for token in tokens:
                print(f"{token.type:<12} {token.value!r} @ {token.pos.line}:{token.pos.column}")
            return 0
        program = Parser(tokens).parse()
        print(dump_ast(program))
        return 0

    world, robot = build_world(args)
    if args.gui:
        RobotLangGUI(source, world=world, robot=robot).run()
        return 0

    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    interpreter = Interpreter(world=world, robot=robot, trace=args.trace)
    interpreter.run(program)
    if args.trace:
        print("Final world:")
        print(world.render(robot))
    return 0
