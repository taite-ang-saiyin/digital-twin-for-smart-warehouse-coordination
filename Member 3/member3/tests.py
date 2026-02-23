import logging

from .avoidance import bug2_step
from .config import configure_planner
from .environment import EnvironmentStub
from .graph import dijkstra_shortest_path, euclidean, load_test_graph, print_adjacency_list
from .interfaces import DYNAMIC_OBSTACLES, ROBOT_GOALS, ROBOT_POSITIONS, set_robot_position
from .planner import get_next_move, get_next_move_with_params, run_small_simulation, shortest_path
from .state import get_robot_mode, reset_planner_state


def test_prompt_1() -> None:
    graph = load_test_graph()
    print_adjacency_list(graph)
    env = EnvironmentStub(graph)
    nearest = env.get_node_from_position(0.2, 1.7)
    print(f"Nearest node to (0.2, 1.7): {nearest}")


def test_prompt_2() -> None:
    graph = load_test_graph()
    path, cost = dijkstra_shortest_path(graph, "n_0_0", "n_2_2")
    print(f"Dijkstra path n_0_0 -> n_2_2: {path}, cost={cost:.2f}")


def test_prompt_3() -> None:
    robot_id = 1
    position = (0.0, 0.0)
    goal = (2.0, 2.0)
    print("Step-by-step movement (global planner only):")
    for _ in range(10):
        next_move = get_next_move_with_params(robot_id, goal, position)
        print(f"  current={position} next={next_move}")
        if next_move is None:
            break
        position = next_move
        if euclidean(position, goal) <= 0.25:
            print("  goal reached")
            break


def test_prompt_4() -> None:
    graph = load_test_graph()
    path, cost = shortest_path(graph, "n_0_0", (2.4, 1.6))
    print(f"A* path to non-node goal (2.4,1.6): {path}, cost={cost:.3f}")


def test_prompt_5() -> None:
    robot_id = 99
    reset_planner_state(clear_path_cache=False)
    position = (0.0, 0.0)
    goal = (5.0, 0.0)
    obstacles = [(2.0, 0.0)]
    print("Bug2 local avoidance test:")
    for step in range(12):
        next_move = bug2_step(robot_id, position, goal, obstacles)
        print(f"  step={step} pos={position} next={next_move} mode={get_robot_mode(robot_id)}")
        if euclidean(next_move, position) < 1e-9:
            break
        position = next_move
        if euclidean(position, goal) <= 0.5:
            print("  near goal")
            break


def test_prompt_6() -> None:
    configure_planner(log_level=logging.INFO)
    reset_planner_state(clear_path_cache=False)
    ROBOT_POSITIONS[1] = (0.0, 0.0)
    ROBOT_GOALS[1] = (2.0, 2.0)
    DYNAMIC_OBSTACLES.clear()
    print("Integration test with dynamic obstacle:")
    for step in range(8):
        if step == 2:
            DYNAMIC_OBSTACLES[:] = [(1.0, 1.0)]
        if step == 5:
            DYNAMIC_OBSTACLES.clear()
        next_move = get_next_move(1)
        print(f"  step={step} pos={ROBOT_POSITIONS[1]} next={next_move} obstacles={DYNAMIC_OBSTACLES}")
        if next_move is None:
            break
        set_robot_position(1, next_move)


def test_prompt_7_dead_end() -> None:
    configure_planner(log_level=logging.INFO)
    reset_planner_state(clear_path_cache=False)
    ROBOT_POSITIONS[1] = (0.0, 0.0)
    ROBOT_GOALS[1] = (2.0, 0.0)
    DYNAMIC_OBSTACLES[:] = [(0.8, 0.0), (0.8, 0.5), (0.8, -0.5), (1.4, 0.0)]
    print("Replanning and stagnation test:")
    for step in range(20):
        next_move = get_next_move(1)
        print(f"  step={step} pos={ROBOT_POSITIONS[1]} next={next_move}")
        if next_move is not None:
            set_robot_position(1, next_move)


def run_all_basic_tests() -> None:
    configure_planner(log_level=logging.INFO)
    test_prompt_1()
    print()
    test_prompt_2()
    print()
    test_prompt_3()
    print()
    test_prompt_4()
    print()
    test_prompt_5()
    print()
    run_small_simulation(steps=10)
