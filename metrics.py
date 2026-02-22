from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict
import csv, os, time

@dataclass
class RobotStats:
    moved: int = 0
    waited: int = 0
    conflicts: int = 0
    last_progress_step: int = 0

@dataclass
class Metrics:
    start_time: float = field(default_factory=time.time)
    step: int = 0
    conflicts_resolved: int = 0
    deadlocks_resolved: int = 0
    robots: Dict[str, RobotStats] = field(default_factory=dict)

    def ensure_robot(self, rid: str):
        if rid not in self.robots:
            self.robots[rid] = RobotStats(last_progress_step=self.step)

class CSVLogger:
    def __init__(self, out_dir: str, filename: str):
        os.makedirs(out_dir, exist_ok=True)
        self.path = os.path.join(out_dir, filename)
        self._init()

    def _init(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow([
                    "time_s","step","robots",
                    "moved_total","waited_total",
                    "conflicts_resolved","deadlocks_resolved"
                ])

    def write(self, m: Metrics):
        t = time.time() - m.start_time
        moved_total = sum(rs.moved for rs in m.robots.values())
        waited_total = sum(rs.waited for rs in m.robots.values())
        with open(self.path, "a", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                round(t,3), m.step, len(m.robots),
                moved_total, waited_total,
                m.conflicts_resolved, m.deadlocks_resolved
            ])