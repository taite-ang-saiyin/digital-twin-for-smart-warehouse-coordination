from __future__ import annotations

from typing import Dict, List

from member4.adapters_mock import MockWorld, MockRobot
from member4.order_generator import Catalog, OrderGenerator
from member4.scheduler import Scheduler, SchedulerConfig


def main():
    # Mock warehouse
    packing = {"P1": (1, 1), "P2": (14, 14)}
    charging = {"C1": (2, 2), "C2": (13, 13)}
    world = MockWorld(packing=packing, charging=charging)

    # Robots
    robots: Dict[str, MockRobot] = {
        "r1": MockRobot("r1", (3, 3)),
        "r2": MockRobot("r2", (10, 10)),
    }
    for rid in robots:
        world.register_robot(rid)

    # Order generator catalog
    catalog = Catalog(
        shelf_positions=[(3, 12), (6, 6), (9, 4), (12, 8)],
        packing_stations=packing,
        item_ids=[f"SKU{i}" for i in range(1, 8)],
    )
    gen = OrderGenerator(catalog, p_new_order=0.30, seed=7)

    # Scheduler
    cfg = SchedulerConfig(
        use_planner_cost=False,
        use_congestion_hint=False,
        reserve_pack_station_early=True,
        low_battery_threshold=0.15,
    )
    sched = Scheduler(world=world, robots=robots, config=cfg)

    # Simulation loop
    for _ in range(1, 31):
        world.step_tick()
        tick = world.current_tick()

        # Create orders
        order = gen.maybe_generate(tick)
        if order:
            sched.submit_order(order)
            print(f"[t={tick}] New order {order.id}: item={order.item_id} shelf={order.shelf_pos} pack={order.pack_station_id}")

        # Schedule
        sched.tick()

        # Robots execute ONE task per tick (demo)
        for rid, r in robots.items():
            finished = r.step()
            if finished:
                # In this demo, scheduler's queue head is the task in progress
                if sched.robot_queues[rid]:
                    task_id = sched.robot_queues[rid].pop(0)
                    sched.report_task_done(rid, task_id, ok=True)
                    print(f"  - {rid} finished task_id={task_id} ({finished['type']})")

        done_orders = sum(1 for o in sched.orders.values() if o.done)
        print(f"[t={tick}] pending_tasks={len(sched.pending_task_ids)} done_orders={done_orders}")

    print("Demo complete.")


if __name__ == "__main__":
    main()