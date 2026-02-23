from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple, List

from .interfaces import (
    IWorldState,
    IRobotAgent,
    RobotSnapshot,
    RobotExecStatus,
    StationSnapshot,
    StationKind,
    Pos,
    RobotId,
    StationId,
    normalize_battery,
)

@dataclass
class _Station:
    id: StationId
    kind: StationKind
    entrance: Pos
    occupied_by: Optional[RobotId] = None


class MockWorld(IWorldState):
    def __init__(self, *, packing: Dict[StationId, Pos], charging: Dict[StationId, Pos]):
        self._tick = 0
        self._stations: Dict[str, _Station] = {}

        for sid, pos in packing.items():
            self._stations[sid] = _Station(id=sid, kind=StationKind.PACK, entrance=pos)
        for sid, pos in charging.items():
            self._stations[sid] = _Station(id=sid, kind=StationKind.CHARGE, entrance=pos)

        self._robot_ids: List[RobotId] = []

    def register_robot(self, robot_id: RobotId) -> None:
        if robot_id not in self._robot_ids:
            self._robot_ids.append(robot_id)

    def step_tick(self) -> None:
        self._tick += 1

    # ---- interface ----
    def current_tick(self) -> int:
        return self._tick

    def list_robot_ids(self) -> Sequence[RobotId]:
        return list(self._robot_ids)

    def get_robot_snapshot(self, robot_id: RobotId) -> RobotSnapshot:
        # Not used by demo scheduler directly (robot adapter provides snapshots)
        raise NotImplementedError("MockWorld.get_robot_snapshot is unused in demo.")

    def list_station_ids(self, kind: Optional[StationKind] = None) -> Sequence[StationId]:
        if kind is None:
            return list(self._stations.keys())
        return [sid for sid, s in self._stations.items() if s.kind == kind]

    def get_station_snapshot(self, station_id: StationId) -> StationSnapshot:
        s = self._stations[station_id]
        return StationSnapshot(id=s.id, kind=s.kind, entrance=s.entrance, occupied_by=s.occupied_by)

    def is_station_free(self, station_id: StationId) -> bool:
        return self._stations[station_id].occupied_by is None

    def claim_station(self, station_id: StationId, robot_id: RobotId) -> bool:
        s = self._stations[station_id]
        if s.occupied_by is None or s.occupied_by == robot_id:
            s.occupied_by = robot_id
            return True
        return False

    def release_station(self, station_id: StationId, robot_id: RobotId) -> None:
        s = self._stations[station_id]
        if s.occupied_by == robot_id:
            s.occupied_by = None

    def find_nearest_free_station(self, kind: StationKind, from_pos: Pos) -> Optional[StationId]:
        candidates = []
        for sid, s in self._stations.items():
            if s.kind != kind:
                continue
            if s.occupied_by is not None:
                continue
            dist = abs(from_pos[0] - s.entrance[0]) + abs(from_pos[1] - s.entrance[1])
            candidates.append((dist, sid))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][1]


class MockRobot(IRobotAgent):
    """
    Demo robot: accepts a task, instantly completes it on step().
    """
    def __init__(self, robot_id: str, start: Pos):
        self._id = robot_id
        self.pos = start
        self.status = RobotExecStatus.IDLE
        self.battery = 1.0
        self.carrying_item: Optional[str] = None
        self._current_task: Optional[Dict[str, Any]] = None
        self._last_task_id: Optional[int] = None

    @property
    def id(self) -> str:
        return self._id

    def get_snapshot(self) -> RobotSnapshot:
        return RobotSnapshot(
            id=self._id,
            pos=self.pos,
            status=self.status,
            battery=self.battery,
            carrying_item=self.carrying_item,
        )

    def assign_task(self, task: Dict[str, Any]) -> None:
        self._current_task = task
        self.status = RobotExecStatus.BUSY

    def calculate_utility(self, task: Dict[str, Any]) -> float:
        # prefer closer tasks; prefer CHARGE if battery low
        if task.get("type") == "CHARGE":
            return (1.0 - self.battery) * 200.0

        loc = task.get("location") or task.get("item_location") or task.get("station_location")
        if loc is None:
            return 0.0
        dist = abs(self.pos[0] - loc[0]) + abs(self.pos[1] - loc[1])
        return 100.0 / (dist + 1.0)

    def step(self) -> Optional[Dict[str, Any]]:
        """
        Execute current task instantly. Returns the finished task dict (or None).
        """
        if self.status != RobotExecStatus.BUSY or not self._current_task:
            return None

        t = self._current_task
        ttype = t["type"]

        if ttype == "MOVE":
            self.pos = tuple(t["location"])
        elif ttype == "PICK":
            self.pos = tuple(t["item_location"])
            self.carrying_item = t.get("item_id")
        elif ttype == "DROP":
            self.pos = tuple(t["station_location"])
            self.carrying_item = None
        elif ttype == "CHARGE":
            self.pos = tuple(t["station_location"])
            self.battery = 1.0

        # drain a little battery unless charging
        if ttype != "CHARGE":
            self.battery = max(0.0, self.battery - 0.02)

        self._current_task = None
        self.status = RobotExecStatus.IDLE
        return t