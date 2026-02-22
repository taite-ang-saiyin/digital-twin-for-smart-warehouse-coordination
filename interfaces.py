from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Tuple

Cell = Tuple[int, int]

@dataclass
class RobotView:
    robot_id: str
    cell: Cell
    status: str  # "MOVING"|"WAITING"|"IDLE"|"BACKOFF"
    goal: Optional[Cell] = None
    path: Optional[List[Cell]] = None

class EnvironmentAPI(Protocol):
    """Member 1 integration."""
    def grid_size(self) -> Tuple[int, int]: ...
    def blocked_cells(self) -> set[Cell]: ...
    def stations(self) -> Dict[str, Cell]: ...
    def is_cell_free(self, cell: Cell) -> bool: ...
    def update_robot_position(self, robot_id: str, cell: Cell) -> None: ...

class PlannerAPI(Protocol):
    """Member 3 integration."""
    def get_path(self, robot_id: str, start: Cell, goal: Cell) -> List[Cell]: ...

class SchedulerAPI(Protocol):
    """Member 4 integration."""
    def get_goal_for_robot(self, robot_id: str) -> Optional[Cell]: ...
    def report_task_progress(self, robot_id: str, cell: Cell) -> None: ...