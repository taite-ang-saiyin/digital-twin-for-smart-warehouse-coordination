import heapq
import math
import time
from typing import Dict, List, Optional

from .avoidance import bug2_step, is_line_blocked, point_to_segment_distance, step_toward
from .config import CONFIG, LOGGER
from .environment import get_environment
from .graph import Graph, euclidean
from .interfaces import (
    ROBOT_GOALS,
    ROBOT_POSITIONS,
    get_current_goal,
    get_robot_position,
    get_robot_sensor,
    set_robot_position,
)
from .state import cache_get, cache_set, get_context, normalize_goal_key
from .types import GoalType, NodeId, Point


def _reconstruct_path(came_from: Dict[NodeId, Optional[NodeId]], goal: NodeId) -> List[NodeId]:
    result: List[NodeId] = []
    node: Optional[NodeId] = goal
    while node is not None:
        result.append(node)
        node = came_from.get(node)
    result.reverse()
    return result


def _astar_nodes(graph: Graph, start_node: NodeId, goal_node: NodeId) -> tuple[Optional[List[NodeId]], float]:
    if start_node not in graph.nodes or goal_node not in graph.nodes:
        return None, math.inf

    queue: List[tuple[float, float, NodeId]] = []
    g_score: Dict[NodeId, float] = {start_node: 0.0}
    came_from: Dict[NodeId, Optional[NodeId]] = {start_node: None}
    heapq.heappush(queue, (euclidean(graph.nodes[start_node], graph.nodes[goal_node]), 0.0, start_node))

    while queue:
        _, current_g, current = heapq.heappop(queue)
        if current == goal_node:
            return _reconstruct_path(came_from, goal_node), g_score[goal_node]
        if current_g > g_score.get(current, math.inf):
            continue

        for neighbor, weight in graph.get_neighbors(current):
            candidate = g_score[current] + weight
            if candidate < g_score.get(neighbor, math.inf):
                g_score[neighbor] = candidate
                came_from[neighbor] = current
                f_score = candidate + euclidean(graph.nodes[neighbor], graph.nodes[goal_node])
                heapq.heappush(queue, (f_score, candidate, neighbor))
    return None, math.inf


def _nearest_node(graph: Graph, point: Point, exclude_prefix: str = "__temp_goal__") -> NodeId:
    candidates = [node_id for node_id in graph.nodes if not node_id.startswith(exclude_prefix)]
    if not candidates:
        raise ValueError("Graph has no permanent nodes.")
    return min(candidates, key=lambda node_id: euclidean(graph.nodes[node_id], point))


def shortest_path(graph: Graph, start: GoalType, goal: GoalType) -> tuple[Optional[List[NodeId]], float]:
    start_node: NodeId = start if isinstance(start, str) else _nearest_node(graph, (float(start[0]), float(start[1])))

    if CONFIG.enable_cache:
        cached = cache_get(graph, start_node, goal)
        if cached is not None:
            LOGGER.debug("A* cache hit start=%s goal=%s", start_node, goal)
            return cached

    temporary_goal: Optional[NodeId] = None
    nearest_goal_anchor: Optional[NodeId] = None
    goal_node: NodeId

    if isinstance(goal, str):
        goal_node = goal
    else:
        goal_point = (float(goal[0]), float(goal[1]))
        temporary_goal = f"__temp_goal__{int(time.time() * 1000000)}"
        nearest_goal_anchor = _nearest_node(graph, goal_point)
        added_weight = euclidean(goal_point, graph.nodes[nearest_goal_anchor])
        graph.nodes[temporary_goal] = goal_point
        graph.edges[temporary_goal] = [(nearest_goal_anchor, added_weight)]
        graph.edges[nearest_goal_anchor].append((temporary_goal, added_weight))
        goal_node = temporary_goal

    try:
        path, total_cost = _astar_nodes(graph, start_node, goal_node)
    finally:
        if temporary_goal is not None and nearest_goal_anchor is not None:
            graph.edges[nearest_goal_anchor] = [
                (neighbor, weight) for neighbor, weight in graph.edges[nearest_goal_anchor] if neighbor != temporary_goal
            ]
            graph.edges.pop(temporary_goal, None)
            graph.nodes.pop(temporary_goal, None)

    if path is None:
        result = (None, math.inf)
    else:
        if temporary_goal is not None and path and path[-1] == temporary_goal:
            path = path[:-1]
        result = (path, total_cost)

    if CONFIG.enable_cache:
        cache_set(graph, start_node, goal, result)
    return result


def _path_cost(graph: Graph, path: List[NodeId]) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for index in range(len(path) - 1):
        source, target = path[index], path[index + 1]
        for neighbor, weight in graph.get_neighbors(source):
            if neighbor == target:
                total += weight
                break
    return total


def _distance_to_path(point: Point, path_coords: List[Point]) -> float:
    if not path_coords:
        return math.inf
    if len(path_coords) == 1:
        return euclidean(point, path_coords[0])
    return min(
        point_to_segment_distance(point, path_coords[index], path_coords[index + 1])
        for index in range(len(path_coords) - 1)
    )


def _build_path_coords(graph: Graph, path_nodes: List[NodeId], goal: GoalType) -> List[Point]:
    coords = [graph.nodes[node_id] for node_id in path_nodes]
    if isinstance(goal, tuple) and (not coords or euclidean(coords[-1], goal) > 1e-6):
        coords.append((float(goal[0]), float(goal[1])))
    return coords


def _compute_global_path(robot_id: int, robot_pos: Point, goal: GoalType) -> bool:
    ctx = get_context(robot_id)
    environment = get_environment()
    graph = environment.get_graph()
    start_node = environment.get_node_from_position(robot_pos[0], robot_pos[1])
    planner_goal: GoalType = goal if isinstance(goal, str) else (float(goal[0]), float(goal[1]))

    started = time.perf_counter()
    path_nodes, total_cost = shortest_path(graph, start_node, planner_goal)
    elapsed = time.perf_counter() - started
    ctx["planning_calls"] = int(ctx["planning_calls"]) + 1
    ctx["planning_time_total"] = float(ctx["planning_time_total"]) + elapsed

    if not path_nodes:
        ctx["global_path"] = []
        ctx["path_coords"] = []
        ctx["last_path_cost"] = math.inf
        LOGGER.warning("Robot %s could not compute a global path", robot_id)
        return False

    ctx["global_path"] = path_nodes
    ctx["path_coords"] = _build_path_coords(graph, path_nodes, goal)
    ctx["last_path_cost"] = total_cost if isinstance(goal, tuple) else _path_cost(graph, path_nodes)
    ctx["replan_count"] = int(ctx["replan_count"]) + 1
    ctx["mode"] = "goto_goal"
    ctx["bug2_failed"] = False
    LOGGER.info("Robot %s global plan updated (%d waypoints)", robot_id, len(path_nodes))
    return True


def _next_subgoal(robot_pos: Point, path_coords: List[Point]) -> Optional[Point]:
    if not path_coords:
        return None
    closest_index = min(range(len(path_coords)), key=lambda idx: euclidean(robot_pos, path_coords[idx]))
    closest_distance = euclidean(robot_pos, path_coords[closest_index])
    if closest_distance <= 0.25 and closest_index + 1 < len(path_coords):
        return path_coords[closest_index + 1]
    if closest_distance > 0.25:
        return path_coords[closest_index]
    return None


def _track_stagnation(robot_id: int, robot_pos: Point) -> bool:
    ctx = get_context(robot_id)
    last_pos = ctx["last_position"]
    if isinstance(last_pos, tuple):
        if euclidean(last_pos, robot_pos) < CONFIG.stagnation_distance:
            ctx["stagnation_counter"] = int(ctx["stagnation_counter"]) + 1
        else:
            ctx["stagnation_counter"] = 0
    else:
        ctx["stagnation_counter"] = 0
    ctx["last_position"] = robot_pos
    return int(ctx["stagnation_counter"]) >= CONFIG.stagnation_steps


def _goal_reached(robot_pos: Point, goal: GoalType, graph: Graph) -> bool:
    if isinstance(goal, str):
        return euclidean(robot_pos, graph.nodes[goal]) <= 0.25
    return euclidean(robot_pos, goal) <= 0.25


def force_replan(robot_id: int) -> None:
    ctx = get_context(robot_id)
    ctx["force_replan"] = True
    LOGGER.info("Robot %s external force_replan requested", robot_id)


def get_next_move(robot_id: int) -> Optional[Point]:
    environment = get_environment()
    graph = environment.get_graph()
    ctx = get_context(robot_id)
    robot_pos = get_robot_position(robot_id)
    goal = get_current_goal(robot_id)
    goal_key = normalize_goal_key(goal)
    obstacles = get_robot_sensor(robot_id)

    if _goal_reached(robot_pos, goal, graph):
        ctx["last_goal_key"] = goal_key
        ctx["last_goal"] = goal
        if not isinstance(ctx["start_position"], tuple):
            ctx["start_position"] = robot_pos
        ctx["mode"] = "goto_goal"
        ctx["force_replan"] = False
        ctx["stagnation_counter"] = 0
        ctx["last_position"] = robot_pos
        LOGGER.debug("Robot %s at goal", robot_id)
        return None

    goal_changed = ctx["last_goal_key"] != goal_key
    stuck = _track_stagnation(robot_id, robot_pos)
    forced = bool(ctx["force_replan"])
    path_coords = ctx["path_coords"] if isinstance(ctx["path_coords"], list) else []
    deviated = bool(path_coords) and _distance_to_path(robot_pos, path_coords) > CONFIG.deviation_threshold
    needs_path = not bool(ctx["global_path"])

    if goal_changed or stuck or forced or deviated or needs_path:
        reasons = []
        if goal_changed:
            reasons.append("goal_changed")
        if stuck:
            reasons.append("stagnation")
        if forced:
            reasons.append("forced")
        if deviated:
            reasons.append("deviation")
        if needs_path:
            reasons.append("no_path")
        LOGGER.info("Robot %s replanning (%s)", robot_id, ",".join(reasons))
        if not _compute_global_path(robot_id, robot_pos, goal):
            ctx["force_replan"] = False
            return None
        ctx["force_replan"] = False

    ctx["last_goal_key"] = goal_key
    ctx["last_goal"] = goal
    if not isinstance(ctx["start_position"], tuple):
        ctx["start_position"] = robot_pos

    path_coords = ctx["path_coords"] if isinstance(ctx["path_coords"], list) else []
    subgoal = _next_subgoal(robot_pos, path_coords)
    if subgoal is None:
        subgoal = graph.nodes[goal] if isinstance(goal, str) else (float(goal[0]), float(goal[1]))

    if not is_line_blocked(robot_pos, subgoal, obstacles):
        if ctx["mode"] == "follow_boundary":
            LOGGER.info("Robot %s leaving Bug2 boundary mode (line clear)", robot_id)
        ctx["mode"] = "goto_goal"
        next_pos = step_toward(robot_pos, subgoal)
    else:
        next_pos = bug2_step(robot_id, robot_pos, subgoal, obstacles)
        if bool(ctx["bug2_failed"]):
            LOGGER.warning("Robot %s Bug2 failed; forcing replan", robot_id)
            force_replan(robot_id)
            if not _compute_global_path(robot_id, robot_pos, goal):
                LOGGER.error("Robot %s global path unreachable after Bug2 failure", robot_id)
                return None
            ctx["bug2_failed"] = False

    ctx["distance_travelled"] = float(ctx["distance_travelled"]) + euclidean(robot_pos, next_pos)
    return next_pos


def get_next_move_with_params(robot_id: int, goal: GoalType, robot_pos: Point) -> Optional[Point]:
    environment = get_environment()
    graph = environment.get_graph()
    start_node = environment.get_node_from_position(robot_pos[0], robot_pos[1])
    planner_goal: GoalType = goal if isinstance(goal, str) else (float(goal[0]), float(goal[1]))
    if isinstance(goal, str) and goal not in graph.nodes:
        return None

    path, _ = shortest_path(graph, start_node, planner_goal)
    if not path:
        return None
    if len(path) == 1:
        if isinstance(goal, tuple) and euclidean(robot_pos, goal) > 0.25:
            return step_toward(robot_pos, goal)
        return None
    return graph.nodes[path[1]]


def run_small_simulation(steps: int = 10) -> None:
    from .config import configure_planner

    configure_planner()
    from .state import reset_planner_state
    from .interfaces import DYNAMIC_OBSTACLES

    reset_planner_state(clear_path_cache=False)
    DYNAMIC_OBSTACLES.clear()
    print("Sequential simulation loop:")
    for step in range(steps):
        if step == 4:
            DYNAMIC_OBSTACLES[:] = [(1.0, 1.0), (1.0, 2.0)]
        if step == 7:
            DYNAMIC_OBSTACLES.clear()
        print(f"Step {step}")
        for robot_id in sorted(ROBOT_POSITIONS):
            next_move = get_next_move(robot_id)
            print(f"  robot={robot_id} pos={ROBOT_POSITIONS[robot_id]} goal={ROBOT_GOALS[robot_id]} next={next_move}")
            if next_move is not None:
                set_robot_position(robot_id, next_move)


def get_robot_metrics(robot_id: int) -> Dict[str, float]:
    ctx = get_context(robot_id)
    planning_calls = int(ctx["planning_calls"])
    planning_time_total = float(ctx["planning_time_total"])
    avg_plan_ms = (planning_time_total / planning_calls) * 1000.0 if planning_calls else 0.0

    goal = get_current_goal(robot_id)
    start_position = (
        ctx["start_position"]
        if isinstance(ctx["start_position"], tuple)
        else ROBOT_POSITIONS.get(robot_id, (0.0, 0.0))
    )
    environment = get_environment()
    goal_pos = environment.get_graph().nodes[goal] if isinstance(goal, str) else goal
    straight = euclidean(start_position, goal_pos)
    travelled = float(ctx["distance_travelled"])
    ratio = travelled / straight if straight > 1e-9 else 1.0

    return {
        "planning_calls": float(planning_calls),
        "avg_planning_ms": avg_plan_ms,
        "replans": float(ctx["replan_count"]),
        "distance_travelled": travelled,
        "path_vs_straight_ratio": ratio,
    }
