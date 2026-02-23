import logging
import random
from typing import Dict, Tuple

import member3 as planner


Point = Tuple[float, float]


def build_large_graph(width: int = 10, height: int = 10) -> planner.Graph:
    graph = planner.Graph()
    blocked_cells = {
        (3, 3),
        (3, 4),
        (3, 5),
        (6, 2),
        (6, 3),
        (6, 4),
        (5, 7),
        (6, 7),
    }

    for y in range(height):
        for x in range(width):
            if (x, y) in blocked_cells:
                continue
            graph.add_node(f"n_{x}_{y}", float(x), float(y))

    for y in range(height):
        for x in range(width):
            if (x, y) in blocked_cells:
                continue
            src = f"n_{x}_{y}"
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in blocked_cells:
                    dst = f"n_{nx}_{ny}"
                    graph.add_edge(src, dst, 1.0, bidirectional=True)
    return graph


def set_demo_state() -> None:
    planner.configure_planner(enable_cache=True, cache_size=1024, log_level=logging.INFO)
    planner.reset_planner_state(clear_cache=True)
    planner.DYNAMIC_OBSTACLES.clear()

    large_graph = build_large_graph()
    planner.set_environment(planner.EnvironmentStub(large_graph))

    planner.ROBOT_POSITIONS.clear()
    planner.ROBOT_POSITIONS.update(
        {
            1: (0.0, 0.0),
            2: (0.0, 9.0),
            3: (9.0, 0.0),
        }
    )

    planner.ROBOT_GOALS.clear()
    planner.ROBOT_GOALS.update(
        {
            1: (9.0, 9.0),
            2: "n_8_1",
            3: (1.0, 8.0),
        }
    )


def update_dynamic_obstacles(step: int) -> None:
    if step < 10:
        planner.DYNAMIC_OBSTACLES[:] = []
        return
    if 10 <= step < 20:
        planner.DYNAMIC_OBSTACLES[:] = [(4.0, 4.0), (4.0, 5.0), (5.0, 5.0)]
        return
    if 20 <= step < 28:
        planner.DYNAMIC_OBSTACLES[:] = [(7.0, 7.0), (7.0, 6.0)]
        return
    planner.DYNAMIC_OBSTACLES[:] = []


def maybe_change_goals(step: int) -> None:
    if step == 22:
        planner.ROBOT_GOALS[2] = (2.0, 2.0)
    if step == 30:
        planner.force_replan(1)


def run_demo(steps: int = 40) -> None:
    set_demo_state()
    start_positions: Dict[int, Point] = dict(planner.ROBOT_POSITIONS)

    print("Starting Member 3 demo simulation")
    for step in range(steps):
        update_dynamic_obstacles(step)
        maybe_change_goals(step)

        if step in (12, 23):
            random.shuffle(planner.DYNAMIC_OBSTACLES)

        print(f"\nStep {step} | dynamic_obstacles={planner.DYNAMIC_OBSTACLES}")
        for robot_id in sorted(planner.ROBOT_POSITIONS):
            current = planner.get_robot_position(robot_id)
            move = planner.get_next_move(robot_id)
            if move is not None:
                planner.set_robot_position(robot_id, move)
            print(
                f"  robot={robot_id} pos={current} goal={planner.get_current_goal(robot_id)} "
                f"next={move} mode={planner.get_robot_mode(robot_id)}"
            )

    print("\nPerformance metrics")
    overall_calls = 0.0
    overall_plan_time_ms = 0.0
    overall_replans = 0.0
    for robot_id in sorted(planner.ROBOT_POSITIONS):
        metrics = planner.get_robot_metrics(robot_id)
        calls = metrics["planning_calls"]
        avg_ms = metrics["avg_planning_ms"]
        replans = metrics["replans"]
        travelled = metrics["distance_travelled"]

        goal = planner.get_current_goal(robot_id)
        goal_pos = planner.get_environment().get_graph().nodes[goal] if isinstance(goal, str) else goal
        straight = planner.euclidean(start_positions[robot_id], goal_pos)
        ratio = travelled / straight if straight > 1e-9 else 1.0

        overall_calls += calls
        overall_plan_time_ms += avg_ms * calls
        overall_replans += replans

        print(
            f"  robot={robot_id} planning_calls={int(calls)} avg_plan_ms={avg_ms:.3f} "
            f"replans={int(replans)} travelled={travelled:.2f} "
            f"path_vs_straight={ratio:.2f}"
        )

    avg_planning_ms = overall_plan_time_ms / overall_calls if overall_calls else 0.0
    print(f"\nOverall average planning time per call: {avg_planning_ms:.3f} ms")
    print(f"Overall replans: {int(overall_replans)}")


if __name__ == "__main__":
    run_demo()
