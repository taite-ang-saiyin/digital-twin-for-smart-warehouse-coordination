from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple
from metrics import Metrics
from deadlock import DeadlockDetector

Cell = Tuple[int, int]

@dataclass
class MoveDecision:
    granted: bool
    reason: str
    suggest_replan: bool = False

class TrafficCoordinator:
    """
    Member 5 core coordination:
    - cell reservation (target cell must be free or owned by same robot)
    - conflict counting
    - deadlock detection + backoff (pause victim)
    """
    def __init__(self, blocked: Set[Cell], metrics: Metrics, deadlock_window: int, backoff_steps: int, max_wait_before_replan: int):
        self.blocked = set(blocked)
        self.metrics = metrics

        self.owner: Dict[Cell, str] = {}         # cell -> robot_id (reservation/occupancy)
        self.last_cell: Dict[str, Cell] = {}     # robot_id -> current cell
        self.wait_count: Dict[str, int] = {}     # robot_id -> consecutive waits
        self.backoff_left: Dict[str, int] = {}   # robot_id -> steps left in backoff pause

        self.deadlock = DeadlockDetector(deadlock_window, backoff_steps)
        self.max_wait_before_replan = max_wait_before_replan

    def register_robot(self, robot_id: str, start: Cell):
        self.metrics.ensure_robot(robot_id)
        self.owner[start] = robot_id
        self.last_cell[robot_id] = start
        self.wait_count.setdefault(robot_id, 0)
        self.backoff_left.setdefault(robot_id, 0)

    def is_backing_off(self, robot_id: str) -> bool:
        return self.backoff_left.get(robot_id, 0) > 0

    def tick_backoff(self):
        for rid in list(self.backoff_left.keys()):
            if self.backoff_left[rid] > 0:
                self.backoff_left[rid] -= 1

    def request_move(self, robot_id: str, frm: Cell, to: Cell) -> MoveDecision:
        self.metrics.ensure_robot(robot_id)

        if self.is_backing_off(robot_id):
            self.metrics.robots[robot_id].waited += 1
            return MoveDecision(False, "backoff", False)

        if to in self.blocked:
            self._deny(robot_id)
            self.metrics.conflicts_resolved += 1
            return MoveDecision(False, "blocked", False)

        current_owner = self.owner.get(to)
        if current_owner is None or current_owner == robot_id:
            # reserve target cell
            self.owner[to] = robot_id
            self.wait_count[robot_id] = 0
            return MoveDecision(True, "granted", False)

        # occupied by other robot
        self._deny(robot_id)
        self.metrics.conflicts_resolved += 1
        suggest = self.wait_count[robot_id] >= self.max_wait_before_replan
        return MoveDecision(False, f"occupied_by:{current_owner}", suggest)

    def commit_move(self, robot_id: str, frm: Cell, to: Cell):
        # release previous cell if still owned
        if self.owner.get(frm) == robot_id:
            del self.owner[frm]
        self.owner[to] = robot_id
        self.last_cell[robot_id] = to
        self.wait_count[robot_id] = 0

        rs = self.metrics.robots[robot_id]
        rs.moved += 1
        rs.last_progress_step = self.metrics.step

    def _deny(self, robot_id: str):
        rs = self.metrics.robots[robot_id]
        rs.waited += 1
        rs.conflicts += 1
        self.wait_count[robot_id] = self.wait_count.get(robot_id, 0) + 1

    def deadlock_check_and_resolve(self):
        last_progress = {rid: self.metrics.robots[rid].last_progress_step for rid in self.metrics.robots}
        action = self.deadlock.check(self.metrics.step, last_progress, self.wait_count)
        if not action:
            return None
        # Trigger backoff
        self.backoff_left[action.victim_id] = action.backoff_steps
        self.metrics.deadlocks_resolved += 1
        return action.victim_id