from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from env.state import WorldState
from sim.logger import EventLogger

Pos = Tuple[int, int]


@dataclass
class SimulationEngine:
    world: WorldState
    logger: Optional[EventLogger] = None
    t: int = 0

    def step(self) -> None:
        """One deterministic timestep."""
        if self.logger:
            self.logger.tick_start(self.t)

        self._expire_dynamic_obstacles()

        # 1) intentions: next cell per robot
        intentions: Dict[str, Pos] = {}
        for rid in sorted(self.world.robots.keys()):
            r = self.world.robots[rid]
            if r.path:
                intentions[rid] = r.path[0]

        # 2) resolve conflicts and apply moves
        occupied_now = {r.pos: r.robot_id for r in self.world.robots.values()}
        target_to_rids: Dict[Pos, list[str]] = {}
        for rid, target in intentions.items():
            target_to_rids.setdefault(target, []).append(rid)

        # Determine winners per target cell (priority = smallest robot_id for now)
        winners: Dict[str, Pos] = {}
        for target, rids in target_to_rids.items():
            rids_sorted = sorted(rids)
            winners[rids_sorted[0]] = target
            for loser in rids_sorted[1:]:
                self._set_wait(loser, "TARGET_CONFLICT")

        # Prevent swaps (A->Bpos and B->Apos): allow only the lower id to proceed
        # Build reverse map: rid -> from_pos
        from_pos = {rid: self.world.robots[rid].pos for rid in winners.keys()}
        for rid_a, to_a in list(winners.items()):
            # if target is occupied by another winner whose target is my from, that's a swap
            occ_rid = occupied_now.get(to_a)
            if occ_rid is None or occ_rid not in winners:
                continue
            rid_b = occ_rid
            to_b = winners[rid_b]
            if to_b == from_pos[rid_a]:
                # swap detected
                if rid_a < rid_b:
                    self._set_wait(rid_b, "SWAP_CONFLICT")
                    winners.pop(rid_b, None)
                else:
                    self._set_wait(rid_a, "SWAP_CONFLICT")
                    winners.pop(rid_a, None)

        # Apply moves (checking static+dynamic+robot occupancy at resolution time)
        # Use updated occupancy as we apply winners in deterministic order
        occupied_next = {r.pos: r.robot_id for r in self.world.robots.values()}
        for rid in sorted(winners.keys()):
            r = self.world.robots[rid]
            target = winners[rid]

            tx, ty = target
            if not self.world.grid.is_static_free(tx, ty):
                self._set_wait(rid, "STATIC_BLOCKED")
                continue
            if not self.world.is_cell_free(tx, ty, consider_robots=False, consider_dynamic=True):
                self._set_wait(rid, "DYNAMIC_BLOCKED")
                continue
            if target in occupied_next and occupied_next[target] != rid:
                self._set_wait(rid, "CELL_OCCUPIED")
                continue

            frm = r.pos
            # commit
            r.pos = target
            r.path.popleft()
            r.status = "MOVING" if r.path else "IDLE"

            # update occupancy
            occupied_next.pop(frm, None)
            occupied_next[target] = rid

            if self.logger:
                self.logger.robot_move(self.t, rid, frm, target)

        # Robots with intentions but not winners (or blocked) should be WAITING if still had path
        for rid in intentions.keys():
            if rid not in winners and self.world.robots[rid].path:
                self.world.robots[rid].status = "WAITING"

        self.t += 1

    def run(self, steps: int) -> None:
        for _ in range(steps):
            self.step()

    def _set_wait(self, robot_id: str, reason: str) -> None:
        self.world.robots[robot_id].status = "WAITING"
        if self.logger:
            self.logger.robot_wait(self.t, robot_id, reason)

    def _expire_dynamic_obstacles(self) -> None:
        remaining = []
        for obs in self.world.dynamic_obstacles:
            obs.ttl_steps -= 1
            if obs.ttl_steps <= 0:
                if self.logger:
                    self.logger.dyn_obs_expire(self.t, obs.cells)
            else:
                remaining.append(obs)
        self.world.dynamic_obstacles = remaining