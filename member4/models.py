from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from .interfaces import Pos, StationId, ItemId, TaskType


class TaskStatus(Enum):
    PENDING = auto()
    ASSIGNED = auto()
    IN_PROGRESS = auto()
    DONE = auto()
    FAILED = auto()


@dataclass
class Task:
    id: int
    type: TaskType
    location: Optional[Pos] = None

    # task-specific data
    item_id: Optional[ItemId] = None
    station_id: Optional[StationId] = None

    # resource constraints (station reservation)
    required_station_id: Optional[StationId] = None

    # scheduling metadata
    est_ticks: int = 1
    deadline_tick: Optional[int] = None

    status: TaskStatus = TaskStatus.PENDING
    order_id: Optional[int] = None

    def to_robot_task_dict(self, station_pos: Optional[Pos] = None) -> Dict[str, Any]:
        """
        Task dict format designed to match Member 2 style later.
        """
        if self.type == TaskType.MOVE:
            return {"type": "MOVE", "location": self.location}

        if self.type == TaskType.PICK:
            return {"type": "PICK", "item_id": self.item_id, "item_location": self.location}

        if self.type == TaskType.DROP:
            return {
                "type": "DROP",
                "item_id": self.item_id,
                "station_id": self.station_id,
                "station_location": station_pos or self.location,
            }

        if self.type == TaskType.CHARGE:
            return {
                "type": "CHARGE",
                "station_id": self.station_id,
                "station_location": station_pos or self.location,
            }

        raise ValueError(f"Unknown task type: {self.type}")


@dataclass
class Order:
    id: int
    item_id: ItemId
    shelf_pos: Pos
    pack_station_id: StationId
    pack_station_pos: Pos
    created_tick: int
    deadline_tick: Optional[int] = None

    task_ids: List[int] = field(default_factory=list)
    assigned: bool = False
    done: bool = False