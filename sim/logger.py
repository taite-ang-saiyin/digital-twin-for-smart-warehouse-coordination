from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EventLogger:
    path_jsonl: str
    enabled: bool = True

    def log(self, event: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        with open(self.path_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def tick_start(self, t: int) -> None:
        self.log({"t": t, "type": "TICK_START"})

    def robot_move(self, t: int, robot_id: str, frm: tuple[int, int], to: tuple[int, int]) -> None:
        self.log({"t": t, "type": "ROBOT_MOVE", "robot_id": robot_id, "from": frm, "to": to})

    def robot_wait(self, t: int, robot_id: str, reason: str) -> None:
        self.log({"t": t, "type": "ROBOT_WAIT", "robot_id": robot_id, "reason": reason})

    def dyn_obs_add(self, t: int, cells: list[tuple[int, int]], ttl: int) -> None:
        self.log({"t": t, "type": "DYN_OBS_ADD", "cells": cells, "ttl": ttl})

    def dyn_obs_expire(self, t: int, cells: list[tuple[int, int]]) -> None:
        self.log({"t": t, "type": "DYN_OBS_EXPIRE", "cells": cells})

    def station_claim(self, t: int, station_id: str, robot_id: str) -> None:
        self.log({"t": t, "type": "STATION_CLAIM", "station_id": station_id, "robot_id": robot_id})

    def station_release(self, t: int, station_id: str, robot_id: str) -> None:
        self.log({"t": t, "type": "STATION_RELEASE", "station_id": station_id, "robot_id": robot_id})