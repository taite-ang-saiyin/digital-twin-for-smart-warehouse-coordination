from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

Cell = Tuple[int, int]

@dataclass
class DeadlockAction:
    victim_id: str
    backoff_steps: int

class DeadlockDetector:
    """
    Simple deadlock detector:
    - If multiple robots have not made progress for deadlock_window steps, choose a victim to back off.
    """
    def __init__(self, deadlock_window: int, backoff_steps: int):
        self.deadlock_window = deadlock_window
        self.backoff_steps = backoff_steps

    def check(self, step: int, last_progress_step: Dict[str, int], wait_counts: Dict[str, int]) -> Optional[DeadlockAction]:
        stuck: List[str] = []
        for rid, lp in last_progress_step.items():
            if (step - lp) >= self.deadlock_window:
                stuck.append(rid)
        if len(stuck) < 2:
            return None

        # Victim = highest wait count (or first)
        victim = max(stuck, key=lambda r: wait_counts.get(r, 0))
        return DeadlockAction(victim_id=victim, backoff_steps=self.backoff_steps)