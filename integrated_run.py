from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


Cell = Tuple[int, int]


ROOT = Path(__file__).resolve().parent
MEMBER1_ROOT = ROOT / "Member 1" / "digital-twin-for-smart-warehouse-coordination"
MEMBER2_ROOT = ROOT / "Member 2" / "digital-twin-for-smart-warehouse-coordination"
MEMBER3_ROOT = ROOT / "Member 3"
MEMBER5_ROOT = ROOT / "Member 5" / "digital-twin-for-smart-warehouse-coordination"


for path in (MEMBER1_ROOT, MEMBER2_ROOT, MEMBER3_ROOT, MEMBER5_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


# Member 1
from env.grid import Grid
from env.graph import build_topological_graph
from env.state import RobotState, StationState, WorldState
from sim.logger import EventLogger

# Member 2
from src.robot.robot_factory import RobotFactory
from src.robot.robot_status import RobotStatus

# Member 3
from member3 import Graph as M3Graph
from member3 import configure_planner as m3_configure_planner
from member3 import shortest_path as m3_shortest_path

# Member 5
from coordinator import TrafficCoordinator
from metrics import CSVLogger, Metrics


LOGGER = logging.getLogger("integrated")


def build_default_world() -> WorldState:
    lines = [
        "####################",
        "#D....#.......#....#",
        "#....##..P....#....#",
        "#....#...#....#....#",
        "#....#...#....#....#",
        "#....#...#....#....#",
        "#....#...#....#....#",
        "#....#...#....#..C.#",
        "#....#...#....#....#",
        "#....#........#....#",
        "#....##########....#",
        "#..................#",
        "####################",
    ]
    grid = Grid.from_ascii(lines)
    topo = build_topological_graph(grid)
    world = WorldState(grid=grid, graph=topo)

    station_index = 1
    charge_index = 1
    depot_index = 1
    for y in range(grid.height):
        for x in range(grid.width):
            ct = grid.cell_type(x, y)
            if ct == "STATION_PACK":
                sid = f"pack_{station_index}"
                station_index += 1
                world.stations[sid] = StationState(station_id=sid, kind="PACK", entrance=(x, y))
            elif ct == "STATION_CHARGE":
                sid = f"charge_{charge_index}"
                charge_index += 1
                world.stations[sid] = StationState(station_id=sid, kind="CHARGE", entrance=(x, y))
            elif ct == "DEPOT":
                sid = f"depot_{depot_index}"
                depot_index += 1
                world.stations[sid] = StationState(station_id=sid, kind="DEPOT", entrance=(x, y))

    return world


class Member1Member2EnvAdapter:
    """Member 2 robot API backed by Member 1 world/logging."""

    def __init__(self, world: WorldState, logger: EventLogger):
        self.world = world
        self.logger = logger
        self.current_time = 0

    def set_tick(self, t: int) -> None:
        self.current_time = t

    def is_valid_cell(self, x: int, y: int) -> bool:
        return self.world.grid.in_bounds(x, y)

    def is_cell_free(self, x: int, y: int) -> bool:
        return self.world.is_cell_free(x, y, consider_robots=True, consider_dynamic=True)

    def get_robot_at(self, x: int, y: int) -> Optional[str]:
        for rid, r in self.world.robots.items():
            if r.pos == (x, y):
                return rid
        return None

    def get_all_robot_positions(self) -> Dict[str, Cell]:
        return {rid: r.pos for rid, r in self.world.robots.items()}

    def get_station_at(self, x: int, y: int) -> Optional[str]:
        for sid, st in self.world.stations.items():
            if st.entrance == (x, y):
                return sid
        return None

    def is_charging_station(self, x: int, y: int) -> bool:
        sid = self.get_station_at(x, y)
        if sid is None:
            return False
        return self.world.stations[sid].kind == "CHARGE"

    def robot_move(self, robot_id: str, from_pos: Cell, to_pos: Cell) -> bool:
        result = self.world.update_robot_position(robot_id, to_pos)
        if not result.get("ok"):
            self.robot_wait(robot_id, str(result.get("reason", "MOVE_REJECTED")))
            return False
        self.logger.robot_move(self.current_time, robot_id, from_pos, to_pos)
        return True

    def robot_wait(self, robot_id: str, reason: str = "CELL_OCCUPIED") -> None:
        self.logger.robot_wait(self.current_time, robot_id, reason)

    def robot_pick(self, robot_id: str, position: Cell, item_id: str) -> None:
        self.logger.log({"t": self.current_time, "type": "ROBOT_PICK", "robot_id": robot_id, "position": position, "item_id": item_id})

    def robot_drop(self, robot_id: str, position: Cell, item_id: str) -> None:
        self.logger.log({"t": self.current_time, "type": "ROBOT_DROP", "robot_id": robot_id, "position": position, "item_id": item_id})

    def robot_charge_start(self, robot_id: str, station_id: str) -> None:
        claim = self.world.claim_station(station_id, robot_id)
        if claim.get("ok"):
            self.logger.station_claim(self.current_time, station_id, robot_id)

    def robot_charge_end(self, robot_id: str, station_id: str) -> None:
        release = self.world.release_station(station_id, robot_id)
        if release.get("ok"):
            self.logger.station_release(self.current_time, station_id, robot_id)


class Member5EnvironmentAdapter:
    """Member 5 environment API backed by Member 1 world state."""

    def __init__(self, world: WorldState):
        self.world = world

    def grid_size(self) -> Tuple[int, int]:
        return self.world.grid.width, self.world.grid.height

    def blocked_cells(self) -> set[Cell]:
        blocked: set[Cell] = set()
        for y in range(self.world.grid.height):
            for x in range(self.world.grid.width):
                if not self.world.grid.is_static_free(x, y):
                    blocked.add((x, y))
        return blocked

    def stations(self) -> Dict[str, Cell]:
        return {sid: st.entrance for sid, st in self.world.stations.items()}

    def is_cell_free(self, cell: Cell) -> bool:
        return self.world.is_cell_free(cell[0], cell[1])

    def update_robot_position(self, robot_id: str, cell: Cell) -> None:
        self.world.update_robot_position(robot_id, cell)


class Member3PlannerAdapter:
    """
    Uses Member 3 A* (`shortest_path`) on a graph converted from Member 1's topological graph.
    Then expands node-level path segments into grid-cell paths for movement/coordinator execution.
    """

    def __init__(self, world: WorldState):
        self.world = world
        self._m3_graph = M3Graph()
        self._m1_to_m3: Dict[int, str] = {}
        self._m3_to_cell: Dict[str, Cell] = {}
        self._cache: Dict[Tuple[Cell, Cell], List[Cell]] = {}
        self._build_member3_graph()

    def _build_member3_graph(self) -> None:
        for node_id, node in self.world.graph.nodes.items():
            m3_id = f"m1_{node_id}"
            self._m1_to_m3[node_id] = m3_id
            self._m3_to_cell[m3_id] = (node.x, node.y)
            self._m3_graph.add_node(m3_id, float(node.x), float(node.y))
        for node_id, neighbors in self.world.graph.adj.items():
            for nb_id, weight in neighbors:
                if node_id < nb_id:
                    self._m3_graph.add_edge(self._m1_to_m3[node_id], self._m1_to_m3[nb_id], float(weight), bidirectional=True)

    def clear_cached_path(self, start: Cell, goal: Cell) -> None:
        self._cache.pop((start, goal), None)

    def get_path(self, robot_id: str, start: Cell, goal: Cell) -> List[Cell]:
        _ = robot_id
        if start == goal:
            return [start]
        cached = self._cache.get((start, goal))
        if cached:
            return list(cached)

        start_m1 = self._nearest_topo_node(start)
        goal_m1 = self._nearest_topo_node(goal)
        if start_m1 is None or goal_m1 is None:
            return [start]

        m3_start = self._m1_to_m3[start_m1]
        m3_goal = self._m1_to_m3[goal_m1]
        node_path, _ = m3_shortest_path(self._m3_graph, m3_start, m3_goal)
        if not node_path:
            return [start]

        expanded: List[Cell] = []
        current = start
        for m3_node in node_path:
            target = self._m3_to_cell[m3_node]
            segment = self._bfs_cells(current, target)
            if not segment:
                continue
            if not expanded:
                expanded.extend(segment)
            else:
                expanded.extend(segment[1:])
            current = target

        if current != goal:
            tail = self._bfs_cells(current, goal)
            if tail:
                if not expanded:
                    expanded.extend(tail)
                else:
                    expanded.extend(tail[1:])

        if not expanded:
            expanded = [start]

        self._cache[(start, goal)] = list(expanded)
        return expanded

    def _nearest_topo_node(self, cell: Cell) -> Optional[int]:
        direct = self.world.graph.nearest_node_id(cell[0], cell[1])
        if direct is not None:
            return direct
        best_id: Optional[int] = None
        best_dist = math.inf
        for node_id, node in self.world.graph.nodes.items():
            dist = abs(node.x - cell[0]) + abs(node.y - cell[1])
            if dist < best_dist:
                best_dist = dist
                best_id = node_id
        return best_id

    def _bfs_cells(self, start: Cell, goal: Cell) -> List[Cell]:
        if start == goal:
            return [start]
        q: deque[Cell] = deque([start])
        prev: Dict[Cell, Optional[Cell]] = {start: None}
        while q:
            x, y = q.popleft()
            for nx, ny in self.world.grid.neighbors4(x, y):
                nxt = (nx, ny)
                if nxt in prev:
                    continue
                if not self.world.grid.is_static_free(nx, ny):
                    continue
                prev[nxt] = (x, y)
                if nxt == goal:
                    return self._reconstruct(prev, goal)
                q.append(nxt)
        return []

    @staticmethod
    def _reconstruct(prev: Dict[Cell, Optional[Cell]], goal: Cell) -> List[Cell]:
        path: List[Cell] = []
        cur: Optional[Cell] = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path


class SimpleScheduler:
    """Placeholder for Member 4: deterministic goals so integrated loop can run."""

    def __init__(self, stations: Dict[str, Cell], robot_ids: Iterable[str]):
        goals = list(stations.values()) or [(1, 1)]
        self._goal_cycle: Dict[str, List[Cell]] = {}
        self._goal_index: Dict[str, int] = {}
        for idx, rid in enumerate(robot_ids):
            ordered = goals[idx % len(goals):] + goals[:idx % len(goals)]
            self._goal_cycle[rid] = ordered
            self._goal_index[rid] = 0

    def get_goal_for_robot(self, robot_id: str) -> Optional[Cell]:
        seq = self._goal_cycle.get(robot_id)
        if not seq:
            return None
        return seq[self._goal_index[robot_id] % len(seq)]

    def report_task_progress(self, robot_id: str, cell: Cell) -> None:
        goal = self.get_goal_for_robot(robot_id)
        if goal is not None and cell == goal:
            self._goal_index[robot_id] = self._goal_index.get(robot_id, 0) + 1


def direction_from_step(frm: Cell, to: Cell) -> Optional[str]:
    dx = to[0] - frm[0]
    dy = to[1] - frm[1]
    mapping = {(1, 0): "RIGHT", (-1, 0): "LEFT", (0, 1): "DOWN", (0, -1): "UP"}
    return mapping.get((dx, dy))


@dataclass
class IntegratedRobotRuntime:
    robot_id: str
    robot: object
    path: List[Cell]
    path_idx: int = 0
    goal: Optional[Cell] = None
    last_status: str = "IDLE"

    @property
    def cell(self) -> Cell:
        return self.robot.position  # type: ignore[attr-defined]


def create_robots(world: WorldState, env_adapter: Member1Member2EnvAdapter) -> Dict[str, IntegratedRobotRuntime]:
    starts: Dict[str, Cell] = {
        "R1": (1, 1),
        "R2": (2, 1),
        "R3": (3, 1),
    }
    robots: Dict[str, IntegratedRobotRuntime] = {}
    factories = [
        RobotFactory.create_universal_robot,
        RobotFactory.create_picker_robot,
        RobotFactory.create_charger_robot,
    ]

    for idx, (rid, start) in enumerate(starts.items()):
        world.robots[rid] = RobotState(robot_id=rid, pos=start)
        robot = factories[idx % len(factories)](rid, start, env_adapter)
        robots[rid] = IntegratedRobotRuntime(robot_id=rid, robot=robot, path=[start])
    return robots


def maybe_build_gui(enable_gui: bool, env5: Member5EnvironmentAdapter):
    if not enable_gui:
        return None, None
    try:
        from interfaces import RobotView
        from gui_tk import DrawWorld, WarehouseGUI
    except Exception as exc:  # pragma: no cover - import failure fallback
        LOGGER.warning("GUI import failed, running headless: %s", exc)
        return None, None

    try:
        w, h = env5.grid_size()
        gui = WarehouseGUI(DrawWorld(w=w, h=h, blocked=env5.blocked_cells(), stations=env5.stations()))
        return gui, RobotView
    except Exception as exc:  # pragma: no cover - display not available
        LOGGER.warning("GUI unavailable, running headless: %s", exc)
        return None, None


def run_simulation(steps: int, enable_gui: bool = False, sleep_s: float = 0.0) -> Dict[str, object]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    m3_configure_planner(log_level=logging.WARNING)

    world = build_default_world()
    out_dir = ROOT / "integrated_output"
    out_dir.mkdir(exist_ok=True)
    events_path = out_dir / "events.jsonl"
    events_path.write_text("", encoding="utf-8")

    event_logger = EventLogger(str(events_path), enabled=True)
    env12 = Member1Member2EnvAdapter(world, event_logger)
    env5 = Member5EnvironmentAdapter(world)
    planner = Member3PlannerAdapter(world)
    metrics = Metrics()
    csv_logger = CSVLogger(str(out_dir), "metrics.csv")

    robots = create_robots(world, env12)
    scheduler = SimpleScheduler(env5.stations(), robots.keys())

    coord = TrafficCoordinator(
        blocked=env5.blocked_cells(),
        metrics=metrics,
        deadlock_window=20,
        backoff_steps=6,
        max_wait_before_replan=8,
    )

    for rid, runtime in robots.items():
        coord.register_robot(rid, runtime.cell)
        env5.update_robot_position(rid, runtime.cell)
        metrics.robots[rid].last_progress_step = 0

    gui, RobotView = maybe_build_gui(enable_gui, env5)

    for t in range(steps):
        metrics.step += 1
        env12.set_tick(t)
        event_logger.tick_start(t)

        coord.tick_backoff()
        victim = coord.deadlock_check_and_resolve()
        if victim and victim in robots:
            robots[victim].last_status = "BACKOFF"

        for rid, runtime in robots.items():
            runtime.goal = scheduler.get_goal_for_robot(rid)
            if runtime.goal is None:
                runtime.path = [runtime.cell]
                runtime.path_idx = 0
                runtime.last_status = "IDLE"
                continue

            need_replan = (
                not runtime.path
                or runtime.path_idx >= len(runtime.path)
                or runtime.path[-1] != runtime.goal
                or runtime.cell not in runtime.path
            )
            if need_replan:
                runtime.path = planner.get_path(rid, runtime.cell, runtime.goal)
                runtime.path_idx = 0
            else:
                try:
                    runtime.path_idx = runtime.path.index(runtime.cell)
                except ValueError:
                    runtime.path = planner.get_path(rid, runtime.cell, runtime.goal)
                    runtime.path_idx = 0

        for rid, runtime in robots.items():
            robot = runtime.robot

            if coord.is_backing_off(rid):
                runtime.last_status = "BACKOFF"
                robot.status = RobotStatus.WAITING  # type: ignore[attr-defined]
                continue

            if runtime.goal is None or runtime.cell == runtime.goal:
                runtime.last_status = "IDLE"
                robot.status = RobotStatus.IDLE  # type: ignore[attr-defined]
                scheduler.report_task_progress(rid, runtime.cell)
                continue

            if not runtime.path or len(runtime.path) < 2:
                runtime.last_status = "WAITING"
                robot.status = RobotStatus.WAITING  # type: ignore[attr-defined]
                env12.robot_wait(rid, "NO_PATH")
                continue

            if runtime.cell not in runtime.path:
                runtime.path = planner.get_path(rid, runtime.cell, runtime.goal)
                runtime.path_idx = 0
            else:
                runtime.path_idx = runtime.path.index(runtime.cell)

            if runtime.path_idx >= len(runtime.path) - 1:
                runtime.last_status = "IDLE"
                robot.status = RobotStatus.IDLE  # type: ignore[attr-defined]
                continue

            nxt = runtime.path[runtime.path_idx + 1]
            decision = coord.request_move(rid, runtime.cell, nxt)
            if not decision.granted:
                runtime.last_status = "WAITING"
                robot.status = RobotStatus.WAITING  # type: ignore[attr-defined]
                env12.robot_wait(rid, reason=decision.reason)
                if decision.suggest_replan:
                    planner.clear_cached_path(runtime.cell, runtime.goal)
                    runtime.path = planner.get_path(rid, runtime.cell, runtime.goal)
                    runtime.path_idx = 0
                continue

            direction = direction_from_step(runtime.cell, nxt)
            if direction is None:
                runtime.last_status = "WAITING"
                robot.status = RobotStatus.WAITING  # type: ignore[attr-defined]
                env12.robot_wait(rid, "NON_ADJACENT_STEP")
                if coord.owner.get(nxt) == rid:
                    coord.owner.pop(nxt, None)
                planner.clear_cached_path(runtime.cell, runtime.goal)
                runtime.path = planner.get_path(rid, runtime.cell, runtime.goal)
                runtime.path_idx = 0
                continue

            frm = runtime.cell
            moved = robot.move(direction)  # type: ignore[attr-defined]
            if moved:
                coord.commit_move(rid, frm, robot.position)  # type: ignore[attr-defined]
                env5.update_robot_position(rid, robot.position)  # type: ignore[attr-defined]
                scheduler.report_task_progress(rid, robot.position)  # type: ignore[attr-defined]
                runtime.last_status = "MOVING"
            else:
                runtime.last_status = "WAITING"
                if coord.owner.get(nxt) == rid:
                    coord.owner.pop(nxt, None)
                if decision.suggest_replan:
                    planner.clear_cached_path(runtime.cell, runtime.goal)

        if gui and RobotView:
            views = []
            for rid, runtime in robots.items():
                status_name = runtime.last_status
                try:
                    status_name = runtime.robot.status.name  # type: ignore[attr-defined]
                except Exception:
                    pass
                views.append(RobotView(robot_id=rid, cell=runtime.cell, status=status_name, goal=runtime.goal, path=runtime.path))
            gui.update(views, metrics)

        if metrics.step % 5 == 0:
            csv_logger.write(metrics)

        if sleep_s > 0:
            time.sleep(sleep_s)

    summary = {
        "steps": steps,
        "events_path": str(events_path),
        "metrics_path": str(out_dir / "metrics.csv"),
        "robot_positions": {rid: runtime.cell for rid, runtime in robots.items()},
        "robot_statuses": {rid: getattr(runtime.robot.status, "name", str(runtime.robot.status)) for rid, runtime in robots.items()},
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrated Member 1/2/3/5 warehouse simulation runner")
    parser.add_argument("--steps", type=int, default=50, help="Number of simulation steps to run")
    parser.add_argument("--gui", action="store_true", help="Enable Member 5 Tkinter GUI")
    parser.add_argument("--sleep", type=float, default=0.0, help="Optional per-step sleep (seconds)")
    args = parser.parse_args()

    summary = run_simulation(steps=args.steps, enable_gui=args.gui, sleep_s=args.sleep)
    print("Integrated run complete")
    print(f"steps={summary['steps']}")
    print(f"events={summary['events_path']}")
    print(f"metrics={summary['metrics_path']}")
    print(f"robot_positions={summary['robot_positions']}")
    print(f"robot_statuses={summary['robot_statuses']}")


if __name__ == "__main__":
    main()
