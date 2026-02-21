import math
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from .config import CONFIG
from .graph import Graph
from .types import GoalType, NodeId


_PATH_CACHE: "OrderedDict[Tuple[int, NodeId, Tuple[str, float, float]], Tuple[Optional[List[NodeId]], float]]" = OrderedDict()
ROBOT_CONTEXT: Dict[int, Dict[str, object]] = {}


def normalize_goal_key(goal: GoalType) -> Tuple[str, float, float]:
    if isinstance(goal, str):
        return ("node", hash(goal), 0.0)
    return ("coord", round(float(goal[0]), 4), round(float(goal[1]), 4))


def cache_get(graph: Graph, start: NodeId, goal: GoalType) -> Optional[Tuple[Optional[List[NodeId]], float]]:
    key = (graph.version, start, normalize_goal_key(goal))
    value = _PATH_CACHE.get(key)
    if value is None:
        return None
    _PATH_CACHE.move_to_end(key)
    return value


def cache_set(graph: Graph, start: NodeId, goal: GoalType, value: Tuple[Optional[List[NodeId]], float]) -> None:
    key = (graph.version, start, normalize_goal_key(goal))
    _PATH_CACHE[key] = value
    _PATH_CACHE.move_to_end(key)
    while len(_PATH_CACHE) > CONFIG.cache_size:
        _PATH_CACHE.popitem(last=False)


def clear_cache() -> None:
    _PATH_CACHE.clear()


def default_robot_context() -> Dict[str, object]:
    return {
        "mode": "goto_goal",
        "hit_point": None,
        "leave_point": None,
        "boundary_start": None,
        "boundary_steps": 0,
        "bug2_failed": False,
        "global_path": [],
        "path_coords": [],
        "last_goal_key": None,
        "last_goal": None,
        "last_position": None,
        "stagnation_counter": 0,
        "force_replan": False,
        "last_path_cost": math.inf,
        "replan_count": 0,
        "planning_calls": 0,
        "planning_time_total": 0.0,
        "distance_travelled": 0.0,
        "start_position": None,
    }


def get_context(robot_id: int) -> Dict[str, object]:
    if robot_id not in ROBOT_CONTEXT:
        ROBOT_CONTEXT[robot_id] = default_robot_context()
    return ROBOT_CONTEXT[robot_id]


def reset_planner_state(clear_path_cache: bool = True, clear_cache: Optional[bool] = None) -> None:
    if clear_cache is not None:
        clear_path_cache = clear_cache
    ROBOT_CONTEXT.clear()
    if clear_path_cache:
        _PATH_CACHE.clear()


def get_robot_mode(robot_id: int) -> str:
    return str(get_context(robot_id)["mode"])
