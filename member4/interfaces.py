from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

Pos = Tuple[int, int]
RobotId = str
StationId = str
ItemId = str


class StationKind(Enum):
    PACK = "pack"
    CHARGE = "charge"


class RobotExecStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    WAITING = auto()
    BLOCKED = auto()
    CHARGING = auto()
    ERROR = auto()


class TaskType(Enum):
    MOVE = auto()
    PICK = auto()
    DROP = auto()
    CHARGE = auto()


@dataclass(frozen=True)
class RobotSnapshot:
    id: RobotId
    pos: Pos
    status: RobotExecStatus
    battery: float  # normalized 0..1
    carrying_item: Optional[ItemId] = None


@dataclass(frozen=True)
class StationSnapshot:
    id: StationId
    kind: StationKind
    entrance: Pos
    occupied_by: Optional[RobotId] = None


@runtime_checkable
class IWorldState(Protocol):
    """Member 1 adapter implements this."""

    def current_tick(self) -> int: ...
    def list_robot_ids(self) -> Sequence[RobotId]: ...
    def get_robot_snapshot(self, robot_id: RobotId) -> RobotSnapshot: ...

    def list_station_ids(self, kind: Optional[StationKind] = None) -> Sequence[StationId]: ...
    def get_station_snapshot(self, station_id: StationId) -> StationSnapshot: ...

    def is_station_free(self, station_id: StationId) -> bool: ...
    def claim_station(self, station_id: StationId, robot_id: RobotId) -> bool: ...
    def release_station(self, station_id: StationId, robot_id: RobotId) -> None: ...

    def find_nearest_free_station(self, kind: StationKind, from_pos: Pos) -> Optional[StationId]: ...


@runtime_checkable
class IRobotAgent(Protocol):
    """Member 2 adapter implements this."""

    @property
    def id(self) -> RobotId: ...

    def get_snapshot(self) -> RobotSnapshot: ...

    def assign_task(self, task: Dict[str, Any]) -> None: ...
    def calculate_utility(self, task: Dict[str, Any]) -> float: ...


@runtime_checkable
class IPathPlanner(Protocol):
    """Optional. Member 4 can use this for better scoring, but does not require it."""
    def estimate_cost(self, start: Pos, goal: Pos) -> float: ...


class MovePermit(Enum):
    ALLOW = auto()
    WAIT = auto()
    REROUTE = auto()


@dataclass(frozen=True)
class CoordinationHint:
    permit: MovePermit
    reason: Optional[str] = None
    suggested_wait_ticks: int = 0
    congestion_score: float = 0.0


@runtime_checkable
class ICoordinator(Protocol):
    """Optional. Usually robots call this, not scheduler."""
    def estimate_congestion(self, start: Pos, goal: Pos) -> float: ...


def normalize_battery(value: float) -> float:
    """If real robot battery is 0..100, convert to 0..1."""
    if value > 1.0:
        return max(0.0, min(1.0, value / 100.0))
    return max(0.0, min(1.0, value))