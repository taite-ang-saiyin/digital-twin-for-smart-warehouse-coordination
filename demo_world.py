from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from interfaces import EnvironmentAPI, PlannerAPI, SchedulerAPI, Cell

@dataclass
class DemoEnv(EnvironmentAPI):
    w: int = 20
    h: int = 20

    def __post_init__(self):
        self._blocked = {(7,7),(12,7),(7,12),(12,12)}
        self._stations = {"PACKING": (10,2), "CHARGING": (10,17)}
        self._robots: Dict[str, Cell] = {}

    def grid_size(self) -> Tuple[int,int]:
        return self.w, self.h

    def blocked_cells(self) -> set[Cell]:
        return set(self._blocked)

    def stations(self) -> Dict[str, Cell]:
        return dict(self._stations)

    def is_cell_free(self, cell: Cell) -> bool:
        return (cell not in self._blocked)

    def update_robot_position(self, robot_id: str, cell: Cell) -> None:
        self._robots[robot_id] = cell

class DemoPlanner(PlannerAPI):
    """Very basic Manhattan path (replace with Member 3)."""
    def get_path(self, robot_id: str, start: Cell, goal: Cell) -> List[Cell]:
        path = [start]
        x,y = start
        gx,gy = goal
        while x != gx or y != gy:
            if gx > x: x += 1
            elif gx < x: x -= 1
            elif gy > y: y += 1
            elif gy < y: y -= 1
            path.append((x,y))
            if len(path) > 200:
                break
        return path

class DemoScheduler(SchedulerAPI):
    """Static goals that force interactions (replace with Member 4)."""
    def __init__(self):
        self.goals = {"R1": (17,17), "R2": (2,17), "R3": (17,2)}

    def get_goal_for_robot(self, robot_id: str) -> Optional[Cell]:
        return self.goals.get(robot_id)

    def report_task_progress(self, robot_id: str, cell: Cell) -> None:
        pass