from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config import CFG
from interfaces import Cell, RobotView, EnvironmentAPI, PlannerAPI, SchedulerAPI
from demo_world import DemoEnv, DemoPlanner, DemoScheduler
from coordinator import TrafficCoordinator
from metrics import Metrics, CSVLogger
from gui_tk import WarehouseGUI, DrawWorld

@dataclass
class RobotRuntime:
    robot_id: str
    cell: Cell
    status: str = "IDLE"
    goal: Optional[Cell] = None
    path: List[Cell] = None
    path_idx: int = 0

def build_demo():
    env: EnvironmentAPI = DemoEnv()
    planner: PlannerAPI = DemoPlanner()
    scheduler: SchedulerAPI = DemoScheduler()
    return env, planner, scheduler

def main():
    env, planner, scheduler = build_demo()
    w, h = env.grid_size()

    metrics = Metrics()
    logger = CSVLogger(CFG.log_dir, CFG.csv_name)

    coord = TrafficCoordinator(
        blocked=env.blocked_cells(),
        metrics=metrics,
        deadlock_window=CFG.deadlock_window,
        backoff_steps=CFG.backoff_steps,
        max_wait_before_replan=CFG.max_wait_before_replan,
    )

    # Init robots (these are just logical agents; Member 2 can replace this object later)
    robots: Dict[str, RobotRuntime] = {
        "R1": RobotRuntime("R1", (2,2)),
        "R2": RobotRuntime("R2", (17,2)),
        "R3": RobotRuntime("R3", (2,17)),
    }

    for rid, r in robots.items():
        coord.register_robot(rid, r.cell)
        env.update_robot_position(rid, r.cell)
        metrics.robots[rid].last_progress_step = 0

    gui = WarehouseGUI(DrawWorld(w=w, h=h, blocked=env.blocked_cells(), stations=env.stations()))

    step_delay = 1.0 / max(1, CFG.fps)

    while True:
        metrics.step += 1

        # Apply backoff countdown
        coord.tick_backoff()

        # Deadlock check (global)
        victim = coord.deadlock_check_and_resolve()
        if victim:
            robots[victim].status = "BACKOFF"

        # Decide goals + paths
        for rid, r in robots.items():
            r.goal = scheduler.get_goal_for_robot(rid)

            if r.goal is None:
                r.status = "IDLE"
                continue

            # If no path or goal changed or reached end -> recompute
            if not r.path or r.path_idx >= len(r.path) or (r.path and r.path[-1] != r.goal):
                r.path = planner.get_path(rid, r.cell, r.goal)
                r.path_idx = 0

        # Request moves
        for rid, r in robots.items():
            # Backoff robots do nothing until backoff ends
            if coord.is_backing_off(rid):
                r.status = "BACKOFF"
                continue

            # if already at goal
            if r.goal and r.cell == r.goal:
                r.status = "IDLE"
                continue

            # choose next step along path
            if not r.path or len(r.path) < 2:
                r.status = "IDLE"
                continue

            # ensure path_idx points to current cell or next
            # find current cell index if needed
            if r.path[r.path_idx] != r.cell:
                try:
                    r.path_idx = r.path.index(r.cell)
                except ValueError:
                    r.path_idx = 0

            nxt_idx = min(r.path_idx + 1, len(r.path) - 1)
            nxt = r.path[nxt_idx]
            if nxt == r.cell:
                r.status = "IDLE"
                continue

            decision = coord.request_move(rid, r.cell, nxt)
            if decision.granted:
                frm = r.cell
                r.cell = nxt
                r.path_idx = nxt_idx
                coord.commit_move(rid, frm, nxt)
                env.update_robot_position(rid, r.cell)
                scheduler.report_task_progress(rid, r.cell)
                r.status = "MOVING"
            else:
                r.status = "WAITING"

        # GUI update
        views: List[RobotView] = []
        for rid, r in robots.items():
            views.append(RobotView(robot_id=rid, cell=r.cell, status=r.status, goal=r.goal, path=r.path))
        gui.update(views, metrics)

        # CSV logging
        if metrics.step % CFG.csv_every_steps == 0:
            logger.write(metrics)

        time.sleep(step_delay)

if __name__ == "__main__":
    main()