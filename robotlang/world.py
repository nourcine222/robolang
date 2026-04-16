from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
import random

from .errors import RuntimeRobotError


DIRS = ["north", "east", "south", "west"]
ARROWS = {"north": "^", "east": ">", "south": "v", "west": "<"}
VECTORS = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}


@dataclass
class RobotState:
    x: int = 0
    y: int = 0
    direction: str = "east"

    def turn(self, degrees: int) -> None:
        if degrees % 90 != 0:
            raise RuntimeRobotError("Turn angle must be a multiple of 90")
        steps = (degrees // 90) % 4
        idx = DIRS.index(self.direction)
        self.direction = DIRS[(idx + steps) % 4]


@dataclass
class World:
    width: int
    height: int
    obstacles: set[tuple[int, int]] = field(default_factory=set)
    goal: tuple[int, int] | None = None

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def obstacle_at(self, x: int, y: int) -> bool:
        return (x, y) in self.obstacles

    def is_goal(self, x: int, y: int) -> bool:
        return self.goal == (x, y)

    def ahead(self, robot: RobotState) -> tuple[int, int]:
        dx, dy = VECTORS[robot.direction]
        return robot.x + dx, robot.y + dy

    def obstacle_ahead(self, robot: RobotState) -> bool:
        nx, ny = self.ahead(robot)
        return (not self.in_bounds(nx, ny)) or self.obstacle_at(nx, ny)

    def move(self, robot: RobotState, steps: int) -> None:
        if steps < 0:
            raise RuntimeRobotError("Move distance must be non-negative")
        for _ in range(steps):
            nx, ny = self.ahead(robot)
            self._assert_walkable(nx, ny)
            robot.x = nx
            robot.y = ny

    def goto(self, robot: RobotState, target_x: int, target_y: int) -> list[tuple[int, int]]:
        path = self.find_path((robot.x, robot.y), (target_x, target_y))
        if path is None:
            raise RuntimeRobotError(f"No path found from ({robot.x}, {robot.y}) to ({target_x}, {target_y})")
        for nx, ny in path[1:]:
            self._assert_walkable(nx, ny)
            robot.x = nx
            robot.y = ny
        return path

    def randomize(self, robot: RobotState, obstacle_count: int | None = None) -> None:
        rng = random.SystemRandom()
        cells = [(x, y) for y in range(self.height) for x in range(self.width)]
        rng.shuffle(cells)

        if not cells:
            return

        robot_pos = cells.pop()
        robot.x, robot.y = robot_pos
        robot.direction = rng.choice(DIRS)

        if obstacle_count is None:
            obstacle_count = max(1, (self.width * self.height) // 8)
        obstacle_count = min(obstacle_count, max(0, len(cells) - 1))

        self.obstacles = set(cells[:obstacle_count])
        remaining = [cell for cell in cells[obstacle_count:] if cell not in self.obstacles and cell != robot_pos]
        self.goal = rng.choice(remaining) if remaining else robot_pos

    def find_path(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
        if start == goal:
            return [start]
        queue = deque([start])
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue:
            x, y = queue.popleft()
            for dx, dy in VECTORS.values():
                nx, ny = x + dx, y + dy
                if not self.in_bounds(nx, ny) or self.obstacle_at(nx, ny):
                    continue
                if (nx, ny) in came_from:
                    continue
                came_from[(nx, ny)] = (x, y)
                if (nx, ny) == goal:
                    return self._reconstruct_path(came_from, goal)
                queue.append((nx, ny))
        return None

    def _reconstruct_path(self, came_from: dict[tuple[int, int], tuple[int, int] | None], goal: tuple[int, int]) -> list[tuple[int, int]]:
        path = [goal]
        current = goal
        while came_from[current] is not None:
            current = came_from[current]  # type: ignore[assignment]
            path.append(current)
        path.reverse()
        return path

    def _assert_walkable(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            raise RuntimeRobotError(f"Robot would leave the grid at ({x}, {y})")
        if self.obstacle_at(x, y):
            raise RuntimeRobotError(f"Robot hit an obstacle at ({x}, {y})")

    def render(self, robot: RobotState) -> str:
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                if robot.x == x and robot.y == y:
                    row.append(ARROWS.get(robot.direction, "R"))
                elif self.goal == (x, y):
                    row.append("G")
                elif (x, y) in self.obstacles:
                    row.append("#")
                else:
                    row.append(".")
            lines.append(" ".join(row))
        return "\n".join(lines)
