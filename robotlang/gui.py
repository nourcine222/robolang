from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
from ast import literal_eval

from .interpreter import Interpreter
from .optimizer import Optimizer
from .parser import Parser
from .tokenizer import Lexer
from .world import RobotState, World


BG = "#050816"
PANEL = "#0b1220"
PANEL_2 = "#0f172a"
ACCENT = "#38bdf8"
ACCENT_2 = "#22c55e"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
WARN = "#f59e0b"
GRID = "#1e293b"
ROBOT = "#f97316"
DEFAULT_WORLD_SIZE = (8, 8)
DEFAULT_START = (0, 0, "east")
DEFAULT_GOAL = (6, 6)
DEFAULT_OBSTACLES = {(3, 1), (4, 3), (5, 5)}

PROJECT_TEXT = (
    "RobotLang is a compilation project built as a tiny DSL for a virtual robot. "
    "The source code is tokenized, parsed into an AST, optimized with constant folding, "
    "compiled to bytecode, and executed on a custom VM that drives the robot on a 2D grid. "
    "This control room shows the robot, the world, and live execution feedback."
)


class RobotLangGUI:
    def __init__(self, source: str, world: World | None = None, robot: RobotState | None = None):
        self.source = source
        if world is None:
            width, height = DEFAULT_WORLD_SIZE
            obstacles, goal = self._default_world_layout(width, height)
            self.world = World(width, height, obstacles=obstacles, goal=goal)
        else:
            self.world = world
        self.robot = robot or RobotState(*DEFAULT_START)

        self.root = tk.Tk()
        self.root.title("RobotLang Mission Control")
        self.root.geometry("1240x820")
        self.root.configure(bg=BG)
        self.root.minsize(1100, 760)

        self.status_var = tk.StringVar(value="SYSTEM READY")
        self.robot_var = tk.StringVar(value=self._robot_text())
        self.goal_var = tk.StringVar(value=self._goal_text())
        self.explain_var = tk.StringVar(value="Walkthrough mode is idle. Run a program to begin.")
        self.step_var = tk.StringVar(value="STEP 0")
        self.walkthrough_delay = 0.7
        self.walkthrough_mode = False
        self.step_count = 0
        self.width_var = tk.StringVar(value=str(self.world.width))
        self.height_var = tk.StringVar(value=str(self.world.height))
        self.start_x_var = tk.StringVar(value=str(self.robot.x))
        self.start_y_var = tk.StringVar(value=str(self.robot.y))
        self.start_dir_var = tk.StringVar(value=self.robot.direction)
        self.goal_x_var = tk.StringVar(value=str(self.world.goal[0] if self.world.goal else 6))
        self.goal_y_var = tk.StringVar(value=str(self.world.goal[1] if self.world.goal else 6))
        self.obstacles_var = tk.StringVar(value=self._format_obstacles(self.world.obstacles))

        self._build_layout()
        self._draw_world(self.world.render(self.robot))

    def run(self) -> None:
        self.root.mainloop()

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=18, pady=(16, 8))

        tk.Label(
            header,
            text="ROBOTLANG // MISSION CONTROL",
            fg=ACCENT,
            bg=BG,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="A futuristic compiler demo for a custom robot language",
            fg=TEXT,
            bg=BG,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 16))

        left = tk.Frame(body, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(16, 0))

        canvas_shell = tk.Frame(left, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1)
        canvas_shell.pack(fill=tk.BOTH, expand=False)

        self.canvas = tk.Canvas(
            canvas_shell,
            width=560,
            height=560,
            bg="#020617",
            highlightthickness=0,
        )
        self.canvas.pack(padx=12, pady=12)

        status_bar = tk.Frame(left, bg=PANEL_2, highlightbackground=GRID, highlightthickness=1)
        status_bar.pack(fill=tk.X, pady=(12, 0))

        tk.Label(status_bar, textvariable=self.status_var, fg=ACCENT_2, bg=PANEL_2, font=("Consolas", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
        tk.Label(status_bar, textvariable=self.step_var, fg=WARN, bg=PANEL_2, font=("Consolas", 10, "bold")).pack(anchor="w", padx=12, pady=(2, 0))
        tk.Label(status_bar, textvariable=self.robot_var, fg=TEXT, bg=PANEL_2, font=("Consolas", 10)).pack(anchor="w", padx=12, pady=(2, 0))
        tk.Label(status_bar, textvariable=self.goal_var, fg=TEXT, bg=PANEL_2, font=("Consolas", 10)).pack(anchor="w", padx=12, pady=(0, 8))

        info_card = tk.Frame(right, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1)
        info_card.pack(fill=tk.X)
        tk.Label(info_card, text="PROJECT BRIEF", fg=ACCENT, bg=PANEL, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        info = tk.Label(
            info_card,
            text=PROJECT_TEXT,
            fg=TEXT,
            bg=PANEL,
            wraplength=600,
            justify="left",
            font=("Segoe UI", 10),
        )
        info.pack(anchor="w", padx=12, pady=(0, 12))

        world_card = tk.Frame(right, bg=PANEL_2, highlightbackground=GRID, highlightthickness=1)
        world_card.pack(fill=tk.X, pady=(12, 0))
        tk.Label(world_card, text="WORLD STUDIO", fg=ACCENT_2, bg=PANEL_2, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        form = tk.Frame(world_card, bg=PANEL_2)
        form.pack(fill=tk.X, padx=12, pady=(0, 10))
        self._add_form_row(form, "Width", self.width_var, 0, 0)
        self._add_form_row(form, "Height", self.height_var, 0, 2)
        self._add_form_row(form, "Start X", self.start_x_var, 1, 0)
        self._add_form_row(form, "Start Y", self.start_y_var, 1, 2)
        self._add_form_row(form, "Direction", self.start_dir_var, 2, 0)
        self._add_form_row(form, "Goal X", self.goal_x_var, 2, 2)
        self._add_form_row(form, "Goal Y", self.goal_y_var, 3, 0)

        tk.Label(form, text="Obstacles", fg=TEXT, bg=PANEL_2, font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(8, 2))
        self.obstacles_entry = tk.Entry(
            form,
            textvariable=self.obstacles_var,
            bg="#020617",
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Consolas", 10),
        )
        self.obstacles_entry.grid(row=5, column=0, columnspan=4, sticky="ew")
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        world_buttons = tk.Frame(world_card, bg=PANEL_2)
        world_buttons.pack(fill=tk.X, padx=12, pady=(0, 12))
        self._button(world_buttons, "APPLY WORLD", self.apply_world_settings, accent=ACCENT).pack(side=tk.LEFT)
        self._button(world_buttons, "RANDOMIZE", self.randomize_world, accent=WARN).pack(side=tk.LEFT, padx=8)
        self._button(world_buttons, "RESET", self.reset_world, accent=ACCENT).pack(side=tk.LEFT)

        explain_card = tk.Frame(right, bg=PANEL_2, highlightbackground=GRID, highlightthickness=1)
        explain_card.pack(fill=tk.X, pady=(12, 0))
        tk.Label(explain_card, text="STEP-BY-STEP EXPLANATION", fg=WARN, bg=PANEL_2, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(
            explain_card,
            textvariable=self.explain_var,
            fg=TEXT,
            bg=PANEL_2,
            wraplength=600,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=12, pady=(0, 12))

        source_card = tk.Frame(right, bg=PANEL, highlightbackground=GRID, highlightthickness=1)
        source_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        tk.Label(source_card, text="SOURCE PROGRAM", fg=ACCENT, bg=PANEL, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        self.editor = scrolledtext.ScrolledText(
            source_card,
            height=18,
            wrap=tk.WORD,
            bg="#020617",
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=ACCENT,
            selectforeground="#020617",
            relief=tk.FLAT,
            font=("Consolas", 11),
        )
        self.editor.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.editor.insert("1.0", self.source)

        controls = tk.Frame(source_card, bg=PANEL)
        controls.pack(fill=tk.X, padx=12, pady=(0, 12))
        self._button(controls, "RUN PROGRAM", self.run_program).pack(side=tk.LEFT)
        self._button(controls, "WALKTHROUGH", self.walkthrough_program, accent=WARN).pack(side=tk.LEFT, padx=8)
        self._button(controls, "RANDOMIZE WORLD", self.randomize_world, accent=WARN).pack(side=tk.LEFT, padx=8)
        self._button(controls, "RESET WORLD", self.reset_world).pack(side=tk.LEFT)

        log_card = tk.Frame(right, bg=PANEL_2, highlightbackground=GRID, highlightthickness=1)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        tk.Label(log_card, text="EXECUTION LOG", fg=ACCENT, bg=PANEL_2, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.log = scrolledtext.ScrolledText(
            log_card,
            height=12,
            wrap=tk.WORD,
            bg="#020617",
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=ACCENT,
            selectforeground="#020617",
            relief=tk.FLAT,
            font=("Consolas", 10),
            state=tk.DISABLED,
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

    def _button(self, parent, text: str, command, accent: str = ACCENT):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg="#020617",
            activebackground=accent,
            activeforeground="#020617",
            relief=tk.FLAT,
            padx=14,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )

    def run_program(self, walkthrough: bool = False) -> None:
        source = self.editor.get("1.0", tk.END)
        try:
            self._clear_log()
            self.step_count = 0
            self.walkthrough_mode = walkthrough
            self.apply_world_settings(silent=True)
            self.explain_var.set(
                "Walkthrough mode enabled. Each instruction will be explained as it runs."
                if walkthrough
                else "Program running at full speed."
            )
            self.step_var.set("STEP 0")
            self._set_status("WALKTHROUGH ACTIVE" if walkthrough else "PROGRAM RUNNING")
            if walkthrough:
                self._walkthrough_stage("Stage 1: tokenizing the source program.")
            tokens = Lexer(source).tokenize()
            if walkthrough:
                self._walkthrough_stage("Stage 2: parsing tokens into an abstract syntax tree.")
            program = Parser(tokens).parse()
            if walkthrough:
                self._walkthrough_stage("Stage 3: optimizing the AST with constant folding.")
            program = Optimizer().optimize(program)
            if walkthrough:
                self._walkthrough_stage("Stage 4: compiling the optimized AST into bytecode.")
            self.robot = RobotState(self.robot.x, self.robot.y, self.robot.direction)
            if walkthrough:
                self._walkthrough_stage("Stage 5: executing bytecode on the virtual machine.")
            interpreter = Interpreter(world=self.world, robot=self.robot, trace=False, on_event=self._handle_event)
            interpreter.run(program)
            self._draw_world(self.world.render(self.robot))
            self._set_status("PROGRAM COMPLETE")
        except Exception as exc:  # noqa: BLE001
            self._set_status("ERROR DETECTED")
            messagebox.showerror("RobotLang error", str(exc))

    def walkthrough_program(self) -> None:
        self.run_program(walkthrough=True)

    def reset_world(self) -> None:
        width = self._safe_dimension(self.width_var.get(), self.world.width, "width")
        height = self._safe_dimension(self.height_var.get(), self.world.height, "height")
        obstacles, goal = self._default_world_layout(width, height)
        self.world = World(width, height, obstacles=obstacles, goal=goal)
        self.robot = RobotState(*DEFAULT_START)
        self._sync_form_from_world()
        self._draw_world(self.world.render(self.robot))
        self._set_status("WORLD RESET")
        self._log("World reset to the default mission layout.")

    def randomize_world(self) -> None:
        self.world.randomize(self.robot)
        self._sync_form_from_world()
        self._draw_world(self.world.render(self.robot))
        self._set_status("WORLD RANDOMIZED")
        self.robot_var.set(self._robot_text())
        self.goal_var.set(self._goal_text())
        self.explain_var.set("The world was randomized: the robot, goal, and obstacles were reshuffled.")
        self._log("World randomized: obstacles, goal, and robot position reshuffled.")

    def apply_world_settings(self, silent: bool = False) -> None:
        try:
            width = self._parse_positive_int(self.width_var.get(), "width")
            height = self._parse_positive_int(self.height_var.get(), "height")
            start_x = self._parse_int(self.start_x_var.get(), "start x")
            start_y = self._parse_int(self.start_y_var.get(), "start y")
            goal_x = self._parse_int(self.goal_x_var.get(), "goal x")
            goal_y = self._parse_int(self.goal_y_var.get(), "goal y")
            direction = self.start_dir_var.get().strip().lower()
            if direction not in {"north", "east", "south", "west"}:
                raise ValueError("direction must be north, east, south, or west")

            obstacles = self._parse_obstacles(self.obstacles_var.get(), width, height)
            if not (0 <= start_x < width and 0 <= start_y < height):
                raise ValueError("start coordinates must be inside the grid")
            if not (0 <= goal_x < width and 0 <= goal_y < height):
                raise ValueError("goal coordinates must be inside the grid")
            if (start_x, start_y) in obstacles:
                raise ValueError("the robot cannot start on an obstacle")
            if (goal_x, goal_y) in obstacles:
                raise ValueError("the goal cannot be placed on an obstacle")

            self.world = World(width, height, obstacles=obstacles, goal=(goal_x, goal_y))
            self.robot = RobotState(start_x, start_y, direction)
            self._sync_form_from_world()
            self._draw_world(self.world.render(self.robot))
            self.robot_var.set(self._robot_text())
            self.goal_var.set(self._goal_text())
            if not silent:
                self._set_status("WORLD UPDATED")
                self.explain_var.set("The world layout was updated from the control panel.")
                self._log(
                    f"World updated: {width}x{height}, start=({start_x}, {start_y}), goal=({goal_x}, {goal_y}), "
                    f"obstacles={len(obstacles)}."
                )
        except Exception as exc:  # noqa: BLE001
            if silent:
                raise
            self._set_status("WORLD UPDATE FAILED")
            messagebox.showerror("RobotLang world editor", str(exc))

    def _parse_positive_int(self, value: str, label: str) -> int:
        number = self._parse_int(value, label)
        if number <= 0:
            raise ValueError(f"{label} must be greater than zero")
        return number

    def _safe_dimension(self, value: str, fallback: int, label: str) -> int:
        try:
            return self._parse_positive_int(value, label)
        except ValueError:
            return fallback

    def _parse_int(self, value: str, label: str) -> int:
        try:
            return int(value.strip())
        except ValueError as exc:
            raise ValueError(f"{label} must be an integer") from exc

    def _parse_obstacles(self, value: str, width: int, height: int) -> set[tuple[int, int]]:
        text = value.strip()
        if not text:
            return set()
        try:
            if text.startswith("[") or text.startswith("{"):
                raw = literal_eval(text)
                pairs = list(raw)
            else:
                pairs = [part.strip() for part in text.split(";") if part.strip()]
            obstacles: set[tuple[int, int]] = set()
            for pair in pairs:
                if isinstance(pair, tuple) and len(pair) == 2:
                    x, y = pair
                else:
                    cleaned = str(pair).strip().strip("()")
                    x_text, y_text = [item.strip() for item in cleaned.split(",")]
                    x, y = int(x_text), int(y_text)
                if not (0 <= x < width and 0 <= y < height):
                    raise ValueError(f"obstacle ({x}, {y}) is outside the grid")
                obstacles.add((x, y))
            return obstacles
        except Exception as exc:  # noqa: BLE001
            raise ValueError("obstacles must look like 1,2; 3,4; 5,6") from exc

    def _sync_form_from_world(self) -> None:
        self.width_var.set(str(self.world.width))
        self.height_var.set(str(self.world.height))
        self.start_x_var.set(str(self.robot.x))
        self.start_y_var.set(str(self.robot.y))
        self.start_dir_var.set(self.robot.direction)
        self.goal_x_var.set(str(self.world.goal[0] if self.world.goal else 0))
        self.goal_y_var.set(str(self.world.goal[1] if self.world.goal else 0))
        self.obstacles_var.set(self._format_obstacles(self.world.obstacles))

    def _handle_event(self, event: dict) -> None:
        if event["kind"] == "step":
            self.step_count += 1
            self._draw_world(event["world"])
            self.robot_var.set(self._robot_text())
            self.goal_var.set(self._goal_text())
            self.step_var.set(f"STEP {self.step_count}")
            self._set_status(event["payload"].upper())
            explanation = self._explain_step(event["payload"])
            self.explain_var.set(explanation)
            self._log(f"Step {self.step_count}: {event['payload']} - {explanation}")
            self.root.update_idletasks()
            self.root.update()
            if self.walkthrough_mode:
                time.sleep(self.walkthrough_delay)
        elif event["kind"] == "print":
            text = f"Output: {event['payload']}"
            self._log(text)
            self.explain_var.set("The program printed a value to the console pane.")
            if self.walkthrough_mode:
                self.root.update()
                time.sleep(self.walkthrough_delay)
        elif event["kind"] == "write":
            text = f"Wrote file: {event['payload']}"
            self._log(text)
            self.explain_var.set("The program wrote a value to a file on disk.")
            if self.walkthrough_mode:
                self.root.update()
                time.sleep(self.walkthrough_delay)

    def _draw_world(self, world_text: str) -> None:
        self.canvas.delete("all")
        size = 62
        lines = world_text.splitlines()
        self.canvas.create_text(
            18,
            14,
            anchor="w",
            fill=ACCENT,
            font=("Consolas", 11, "bold"),
            text="GRID STATUS",
        )
        for y, line in enumerate(lines):
            cells = line.split(" ")
            for x, cell in enumerate(cells):
                x1 = x * size + 18
                y1 = y * size + 34
                x2 = x1 + size - 8
                y2 = y1 + size - 8
                fill = "#111827"
                outline = "#334155"
                if cell == "#":
                    fill = "#7c2d12"
                    outline = "#fb923c"
                elif cell == "G":
                    fill = "#064e3b"
                    outline = "#34d399"
                elif cell in {"^", ">", "v", "<"}:
                    fill = "#ea580c"
                    outline = "#fdba74"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=cell,
                    fill="#f8fafc",
                    font=("Consolas", 18, "bold"),
                )
        self.canvas.create_rectangle(14, 30, 14 + size * len(lines[0].split(" ")), 34 + size * len(lines), outline=ACCENT, width=2)

    def _clear_log(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def _log(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _explain_step(self, action: str) -> str:
        mapping = {
            "move": "The VM evaluated the move distance, checked grid bounds, then advanced the robot cell by cell.",
            "turn": "The VM rotated the robot in 90-degree steps to update its facing direction.",
            "wait": "The VM consumed a wait instruction, which is useful for pacing a program in the simulation.",
            "goto": "The VM used path planning to move the robot toward the selected target square.",
            "randomize": "The world was reshuffled so obstacles, goal, and robot position changed for a new mission layout.",
            "print": "The VM sent a value to the output pane so the program can report results.",
        }
        return mapping.get(action, f"The VM executed the {action} instruction and updated the robot world.")

    def _walkthrough_stage(self, message: str) -> None:
        self._log(message)
        self.explain_var.set(message)
        self.root.update_idletasks()
        self.root.update()
        time.sleep(self.walkthrough_delay)

    def _add_form_row(self, parent, label: str, var: tk.StringVar, row: int, col: int) -> None:
        tk.Label(parent, text=label, fg=TEXT, bg=PANEL_2, font=("Segoe UI", 10, "bold")).grid(
            row=row, column=col, sticky="w", padx=(0, 8), pady=(4, 2)
        )
        entry = tk.Entry(
            parent,
            textvariable=var,
            bg="#020617",
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Consolas", 10),
        )
        entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 8))

    def _format_obstacles(self, obstacles: set[tuple[int, int]]) -> str:
        if not obstacles:
            return ""
        return "; ".join(f"{x},{y}" for x, y in sorted(obstacles))

    def _default_world_layout(self, width: int, height: int) -> tuple[set[tuple[int, int]], tuple[int, int]]:
        obstacles = {
            (x, y)
            for x, y in DEFAULT_OBSTACLES
            if 0 <= x < width and 0 <= y < height
        }
        goal_x = min(DEFAULT_GOAL[0], max(0, width - 1))
        goal_y = min(DEFAULT_GOAL[1], max(0, height - 1))
        goal = (goal_x, goal_y)
        if goal in obstacles:
            goal = next(
                ((x, y) for y in range(height) for x in range(width) if (x, y) not in obstacles),
                (0, 0),
            )
        return obstacles, goal

    def _robot_text(self) -> str:
        return f"ROBOT  x={self.robot.x}  y={self.robot.y}  dir={self.robot.direction}"

    def _goal_text(self) -> str:
        return f"GOAL   {self.world.goal}"
