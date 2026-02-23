from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
import itertools

from .interfaces import (
    IWorldState,
    IRobotAgent,
    IPathPlanner,
    ICoordinator,
    Pos,
    RobotExecStatus,
    StationKind,
    TaskType,
)
from .models import Order, Task, TaskStatus


@dataclass
class SchedulerConfig:
    use_planner_cost: bool = False          # if planner provided, use it to score distance
    use_congestion_hint: bool = False       # if coordinator provided, add congestion penalty
    reserve_pack_station_early: bool = True # claim station before dispatching MOVE-to-pack / DROP
    low_battery_threshold: float = 0.15     # below this -> prefer charging tasks


class TaskFactory:
    def __init__(self):
        self._tid = itertools.count(1)

    def tasks_for_order(self, order: Order) -> List[Task]:
        """
        Order chain:
          MOVE to shelf -> PICK -> MOVE to pack -> DROP
        """
        def t(**kwargs) -> Task:
            return Task(id=next(self._tid), order_id=order.id, **kwargs)

        tasks = [
            t(type=TaskType.MOVE, location=order.shelf_pos, deadline_tick=order.deadline_tick),
            t(type=TaskType.PICK, location=order.shelf_pos, item_id=order.item_id, est_ticks=3, deadline_tick=order.deadline_tick),
            t(
                type=TaskType.MOVE,
                location=order.pack_station_pos,
                station_id=order.pack_station_id,
                required_station_id=order.pack_station_id,
                deadline_tick=order.deadline_tick,
            ),
            t(
                type=TaskType.DROP,
                location=order.pack_station_pos,
                station_id=order.pack_station_id,
                required_station_id=order.pack_station_id,
                item_id=order.item_id,
                est_ticks=3,
                deadline_tick=order.deadline_tick,
            ),
        ]
        order.task_ids = [x.id for x in tasks]
        return tasks

    def charge_task(self, station_id: str, station_pos: Pos) -> Task:
        return Task(
            id=next(self._tid),
            type=TaskType.CHARGE,
            location=station_pos,
            station_id=station_id,
            required_station_id=station_id,
            est_ticks=20,
        )


class Scheduler:
    """
    Member 4 standalone scheduler that communicates ONLY via interfaces.py.

    - Reads robot + station state from IWorldState
    - Assigns tasks via IRobotAgent.assign_task()
    - Optionally uses IPathPlanner/I Coordinator for better scoring
    """

    def __init__(
        self,
        *,
        world: IWorldState,
        robots: Dict[str, IRobotAgent],
        planner: Optional[IPathPlanner] = None,
        coordinator: Optional[ICoordinator] = None,
        config: Optional[SchedulerConfig] = None,
    ):
        self.world = world
        self.robots = robots
        self.planner = planner
        self.coordinator = coordinator
        self.cfg = config or SchedulerConfig()

        self.orders: Dict[int, Order] = {}
        self.tasks: Dict[int, Task] = {}
        self.pending_task_ids: List[int] = []
        self.robot_queues: Dict[str, List[int]] = {}

        self.task_factory = TaskFactory()

    # -------------------- public API --------------------

    def submit_order(self, order: Order) -> None:
        self.orders[order.id] = order
        tasks = self.task_factory.tasks_for_order(order)
        for t in tasks:
            self.tasks[t.id] = t
            self.pending_task_ids.append(t.id)

    def tick(self) -> None:
        """
        Called each simulation tick by Member 1 loop (later),
        or by demo_main (standalone).
        """
        for rid, robot in self.robots.items():
            self.robot_queues.setdefault(rid, [])
            snap = robot.get_snapshot()

            if snap.status != RobotExecStatus.IDLE:
                continue

            # If robot already has queued tasks but is idle, dispatch the next one.
            if self.robot_queues[rid]:
                self._dispatch_next(rid)
                continue

            # Assign new work
            self._assign_best_chain_to_robot(rid)

    def report_task_done(self, robot_id: str, task_id: int, ok: bool = True) -> None:
        t = self.tasks[task_id]
        t.status = TaskStatus.DONE if ok else TaskStatus.FAILED

        # Release station after DROP/CHARGE completion (simple rule)
        if t.type in (TaskType.DROP, TaskType.CHARGE) and t.required_station_id:
            self.world.release_station(t.required_station_id, robot_id)

        # Mark order done if all tasks done
        if t.order_id is not None:
            o = self.orders[t.order_id]
            if all(self.tasks[tid].status == TaskStatus.DONE for tid in o.task_ids):
                o.done = True

    # -------------------- scheduling --------------------

    def _assign_best_chain_to_robot(self, rid: str) -> None:
        robot = self.robots[rid]
        snap = robot.get_snapshot()

        # Battery-first: if low, schedule charge
        if snap.battery <= self.cfg.low_battery_threshold:
            self._try_assign_charge(rid, snap.pos)
            return

        best_tid: Optional[int] = None
        best_score = float("-inf")

        tick = self.world.current_tick()

        for tid in list(self.pending_task_ids):
            t = self.tasks[tid]
            if t.status != TaskStatus.PENDING:
                continue

            if not self._is_task_feasible_now(rid, t):
                continue

            # Score using robot utility (works with Member 2 robot.calculate_utility later)
            score = self._score_task(robot, snap.pos, t, tick)

            if score > best_score:
                best_score = score
                best_tid = tid

        if best_tid is None:
            return

        chosen = self.tasks[best_tid]

        # Claim station early if required (prevents double-booking)
        if self.cfg.reserve_pack_station_early and chosen.required_station_id:
            if not self.world.claim_station(chosen.required_station_id, rid):
                return  # can’t claim now, try next tick

        # Assign the whole order chain to keep coherence
        chosen.status = TaskStatus.ASSIGNED
        self.pending_task_ids.remove(best_tid)
        self.robot_queues[rid].append(best_tid)

        if chosen.order_id is not None:
            self._enqueue_rest_of_order_chain(rid, chosen.order_id, skip_task_id=best_tid)

        self._dispatch_next(rid)

    def _try_assign_charge(self, rid: str, from_pos: Pos) -> None:
        station_id = self.world.find_nearest_free_station(StationKind.CHARGE, from_pos)
        if station_id is None:
            return

        st = self.world.get_station_snapshot(station_id)
        if not self.world.claim_station(station_id, rid):
            return

        charge_task = self.task_factory.charge_task(station_id, st.entrance)
        self.tasks[charge_task.id] = charge_task
        charge_task.status = TaskStatus.ASSIGNED
        self.robot_queues[rid].append(charge_task.id)

        self._dispatch_next(rid)

    def _enqueue_rest_of_order_chain(self, rid: str, order_id: int, skip_task_id: int) -> None:
        o = self.orders[order_id]
        for tid in o.task_ids:
            if tid == skip_task_id:
                continue
            t = self.tasks[tid]
            if t.status == TaskStatus.PENDING:
                # NOTE: do NOT claim pack station here again;
                # it was claimed when first required task was chosen.
                t.status = TaskStatus.ASSIGNED
                self.pending_task_ids.remove(tid)
                self.robot_queues[rid].append(tid)

    def _dispatch_next(self, rid: str) -> None:
        if not self.robot_queues[rid]:
            return

        robot = self.robots[rid]
        tid = self.robot_queues[rid][0]
        t = self.tasks[tid]
        t.status = TaskStatus.IN_PROGRESS

        # Provide station_pos for DROP/CHARGE keys
        station_pos = t.location
        task_dict = t.to_robot_task_dict(station_pos=station_pos)

        robot.assign_task(task_dict)

    def _is_task_feasible_now(self, rid: str, t: Task) -> bool:
        if t.required_station_id:
            # allow if free or already occupied by this robot (some impls may keep claim)
            st = self.world.get_station_snapshot(t.required_station_id)
            if st.occupied_by is not None and st.occupied_by != rid:
                return False
        return True

    def _score_task(self, robot: IRobotAgent, robot_pos: Pos, t: Task, tick: int) -> float:
        # Base score from robot's utility
        task_dict = t.to_robot_task_dict(station_pos=t.location)
        score = float(robot.calculate_utility(task_dict))

        # Optional: use planner cost instead of raw utility distance effect
        if self.cfg.use_planner_cost and self.planner and t.location is not None:
            cost = float(self.planner.estimate_cost(robot_pos, t.location))
            score += 50.0 / (cost + 1.0)

        # Optional: congestion penalty
        if self.cfg.use_congestion_hint and self.coordinator and t.location is not None:
            congestion = float(self.coordinator.estimate_congestion(robot_pos, t.location))
            score -= congestion

        # Deadline boost
        if t.deadline_tick is not None:
            ticks_left = max(1, t.deadline_tick - tick)
            score += 10.0 / ticks_left

        # Small penalty if requires station (to reduce contention)
        if t.required_station_id is not None:
            score -= 0.5

        return score