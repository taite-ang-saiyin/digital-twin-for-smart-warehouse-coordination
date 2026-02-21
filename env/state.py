from __future__ import annotations
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple
from collections import deque

from .grid import Grid
from .graph import TopoGraph

Pos = Tuple[int, int]


@dataclass
class RobotState:
    robot_id: str
    pos: Pos
    status: str = "IDLE"  # IDLE | MOVING | WAITING | CHARGING | PICKING | DROPPING | FAILED
    path: Deque[Pos] = field(default_factory=deque)  # path in grid cells
    task_id: Optional[str] = None
    battery: float = 1.0


@dataclass
class StationState:
    station_id: str
    kind: str  # PACK | CHARGE
    entrance: Pos
    occupied_by: Optional[str] = None


@dataclass
class ItemState:
    item_id: str
    location: str  # e.g. "CELL:x,y" or "ROBOT:rid" or "STATION:sid"
    status: str = "STORED"  # STORED | IN_TRANSIT | PACKED


@dataclass
class DynamicObstacle:
    cells: List[Pos]
    ttl_steps: int


@dataclass
class WorldState:
    grid: Grid
    graph: TopoGraph
    robots: Dict[str, RobotState] = field(default_factory=dict)
    stations: Dict[str, StationState] = field(default_factory=dict)
    items: Dict[str, ItemState] = field(default_factory=dict)
    dynamic_obstacles: List[DynamicObstacle] = field(default_factory=list)

    # ---- Read APIs ----
    def get_graph(self) -> TopoGraph:
        return self.graph

    def is_cell_free(self, x: int, y: int, *, consider_robots: bool = True, consider_dynamic: bool = True) -> bool:
        if not self.grid.is_static_free(x, y):
            return False

        if consider_dynamic:
            for obs in self.dynamic_obstacles:
                if (x, y) in obs.cells:
                    return False

        if consider_robots:
            for r in self.robots.values():
                if r.pos == (x, y):
                    return False

        return True

    def get_robot_state(self, robot_id: str) -> RobotState:
        return self.robots[robot_id]

    def get_station_state(self, station_id: str) -> StationState:
        return self.stations[station_id]

    def get_item_state(self, item_id: str) -> ItemState:
        return self.items[item_id]

    # ---- Write APIs (validated) ----
    def update_robot_position(self, robot_id: str, new_pos: Pos) -> Dict[str, object]:
        (x, y) = new_pos
        if not self.grid.in_bounds(x, y):
            return {"ok": False, "reason": "OUT_OF_BOUNDS"}

        if not self.grid.is_static_free(x, y):
            return {"ok": False, "reason": "STATIC_BLOCKED"}

        # Note: dynamic/robot collision checks are typically handled in engine conflict resolution.
        self.robots[robot_id].pos = new_pos
        return {"ok": True}

    def set_robot_path(self, robot_id: str, path: List[Pos]) -> Dict[str, object]:
        self.robots[robot_id].path = deque(path)
        self.robots[robot_id].status = "MOVING" if path else "IDLE"
        return {"ok": True}

    def add_dynamic_obstacle(self, cells: List[Pos], ttl_steps: int) -> Dict[str, object]:
        if ttl_steps <= 0:
            return {"ok": False, "reason": "BAD_TTL"}
        for (x, y) in cells:
            if not self.grid.in_bounds(x, y):
                return {"ok": False, "reason": "OUT_OF_BOUNDS_CELL"}
        self.dynamic_obstacles.append(DynamicObstacle(cells=cells, ttl_steps=ttl_steps))
        return {"ok": True}

    def claim_station(self, station_id: str, robot_id: str) -> Dict[str, object]:
        st = self.stations[station_id]
        if st.occupied_by is not None and st.occupied_by != robot_id:
            return {"ok": False, "reason": "STATION_OCCUPIED"}
        st.occupied_by = robot_id
        return {"ok": True}

    def release_station(self, station_id: str, robot_id: str) -> Dict[str, object]:
        st = self.stations[station_id]
        if st.occupied_by != robot_id:
            return {"ok": False, "reason": "NOT_OWNER"}
        st.occupied_by = None
        return {"ok": True}