# RobotLang

RobotLang is a small DSL for a virtual robot, built for a compilation project.

## What it supports

- Variables with lexical scopes
- Arithmetic and logical expressions
- `if` / `else`
- `while`
- `repeat`
- Procedures with `return`
- `break` and `continue`
- Arrays and indexing
- `randomize` to reshuffle the robot world
- File I/O with `read(...)` and `write ...`
- Path planning with `goto(...)` and `pathfind(...)`
- AST printing with `--ast`
- Token printing with `--tokens`
- A futuristic Tkinter GUI simulator with `--gui`
- A world studio in the GUI to edit size, start, goal, and obstacles
- Bytecode compilation and a small virtual machine
- Constant folding optimization

## Run

```bash
python -m robotlang --demo
python -m robotlang --demo --trace
python -m robotlang --gui
python -m robotlang --ast examples/demo.rbt
python -m robotlang --tokens examples/demo.rbt
```

Run a file:

```bash
python -m robotlang examples/demo.rbt
```

## GUI world studio

In the GUI, use **World Studio** to customize:

- grid width and height
- robot start position and direction
- goal position
- obstacles using entries like `1,2; 3,4; 5,6`

Then click **Apply World** before running the program.

## Sample syntax

```txt
let step = 1;
let nums = [1, 2, 3];

proc walk(n) {
  let i = 0;
  while i < n {
    move step;
    i = i + 1;
  }
  return n;
}

print walk(3);
randomize;
goto(6, 6);
print at_goal;
```

## Tests

```bash
python -m unittest discover -s tests
```
