import unittest

from robotlang.interpreter import Interpreter
from robotlang.parser import Parser
from robotlang.tokenizer import Lexer
from robotlang.world import RobotState, World
from robotlang.errors import SemanticError, LexError, RuntimeRobotError


def run_source(source: str, world=None, robot=None):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    interpreter = Interpreter(world=world, robot=robot, trace=False)
    return interpreter.run(program), interpreter


class RobotLangTests(unittest.TestCase):
    def test_demo_runs(self):
        world = World(8, 8, obstacles={(3, 1), (4, 3), (5, 5)}, goal=(6, 6))
        robot = RobotState(0, 0, "east")
        output, interpreter = run_source(
            """
let step = 1;

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
goto(6, 6);
print at_goal;
""",
            world=world,
            robot=robot,
        )
        self.assertEqual(output[-1], "True")
        self.assertEqual((interpreter.robot.x, interpreter.robot.y), (6, 6))

    def test_variables_arrays_and_indexing(self):
        output, _ = run_source("let nums = [1, 2, 3]; print nums[1];")
        self.assertEqual(output[-1], "2")

    def test_while_and_return(self):
        source = """
proc sum_to(n) {
  let i = 0;
  let total = 0;
  while i <= n {
    total = total + i;
    i = i + 1;
  }
  return total;
}

print sum_to(4);
"""
        output, _ = run_source(source)
        self.assertEqual(output[-1], "10")

    def test_pathfind_builtin(self):
        source = "let p = pathfind(3, 0); print p[0][0];"
        output, _ = run_source(source)
        self.assertEqual(output[-1], "0")

    def test_break_and_continue(self):
        source = """
let i = 0;
let total = 0;
while i < 5 {
  i = i + 1;
  if i == 3 {
    continue;
  }
  total = total + i;
  if i == 4 {
    break;
  }
}
print total;
"""
        output, _ = run_source(source)
        self.assertEqual(output[-1], "7")

    def test_randomize_statement(self):
        output, interpreter = run_source("randomize; print 1;")
        self.assertEqual(output[-1], "1")
        self.assertTrue(interpreter.world.in_bounds(interpreter.robot.x, interpreter.robot.y))

    def test_parse_error(self):
        with self.assertRaises(LexError):
            Lexer('print "hello').tokenize()

    def test_semantic_error(self):
        with self.assertRaises(SemanticError):
            run_source("print x;")

    def test_runtime_error(self):
        world = World(3, 3, obstacles=set(), goal=(2, 2))
        robot = RobotState(0, 0, "east")
        with self.assertRaises(RuntimeRobotError):
            run_source("move 99;", world=world, robot=robot)


if __name__ == "__main__":
    unittest.main()
