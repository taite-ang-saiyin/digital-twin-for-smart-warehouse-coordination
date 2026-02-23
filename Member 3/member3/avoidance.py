import math
from typing import Iterable, List, Tuple

from .config import CONFIG, LOGGER
from .graph import euclidean
from .state import get_context
from .types import Point


def step_toward(start: Point, goal: Point, step_size: float = None) -> Point:
    step = CONFIG.step_size if step_size is None else step_size
    dist = euclidean(start, goal)
    if dist <= step:
        return goal
    dx = (goal[0] - start[0]) / dist
    dy = (goal[1] - start[1]) / dist
    return (round(start[0] + dx * step, 4), round(start[1] + dy * step, 4))


def point_to_segment_distance(point: Point, seg_a: Point, seg_b: Point) -> float:
    ax, ay = seg_a
    bx, by = seg_b
    px, py = point
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    denom = abx * abx + aby * aby
    if denom == 0:
        return euclidean(point, seg_a)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    closest = (ax + t * abx, ay + t * aby)
    return euclidean(point, closest)


def is_line_blocked(start: Point, goal: Point, obstacles: Iterable[Point], clearance: float = 0.45) -> bool:
    if euclidean(start, goal) < 1e-9:
        return False
    for obstacle in obstacles:
        if point_to_segment_distance(obstacle, start, goal) <= clearance:
            return True
    return False


def _is_position_clear(candidate: Point, obstacles: Iterable[Point], min_dist: float = 0.65) -> bool:
    return all(euclidean(candidate, obs) > min_dist for obs in obstacles)


def _direction_from_vec(vec: Tuple[float, float]) -> Point:
    mag = math.hypot(vec[0], vec[1])
    if mag < 1e-9:
        return (0.0, 0.0)
    return (vec[0] / mag, vec[1] / mag)


def _boundary_follow_step(robot_pos: Point, goal_pos: Point, obstacles: List[Point]) -> Point:
    if not obstacles:
        return step_toward(robot_pos, goal_pos)

    nearest = min(obstacles, key=lambda p: euclidean(robot_pos, p))
    vx = nearest[0] - robot_pos[0]
    vy = nearest[1] - robot_pos[1]
    left_perp = _direction_from_vec((-vy, vx))
    away = _direction_from_vec((robot_pos[0] - nearest[0], robot_pos[1] - nearest[1]))
    to_goal = _direction_from_vec((goal_pos[0] - robot_pos[0], goal_pos[1] - robot_pos[1]))
    right_perp = _direction_from_vec((vy, -vx))

    for direction in (left_perp, away, to_goal, right_perp):
        candidate = (
            round(robot_pos[0] + direction[0] * CONFIG.step_size, 4),
            round(robot_pos[1] + direction[1] * CONFIG.step_size, 4),
        )
        if _is_position_clear(candidate, obstacles):
            return candidate
    return robot_pos


def bug2_step(robot_id: int, robot_pos: Point, goal_pos: Point, obstacles: List[Point]) -> Point:
    ctx = get_context(robot_id)
    mode = str(ctx["mode"])

    if mode == "goto_goal":
        if is_line_blocked(robot_pos, goal_pos, obstacles):
            ctx["mode"] = "follow_boundary"
            ctx["hit_point"] = robot_pos
            ctx["boundary_start"] = robot_pos
            ctx["boundary_steps"] = 0
            LOGGER.info("Robot %s Bug2 mode switch: goto_goal -> follow_boundary", robot_id)
            return _boundary_follow_step(robot_pos, goal_pos, obstacles)
        return step_toward(robot_pos, goal_pos)

    next_pos = _boundary_follow_step(robot_pos, goal_pos, obstacles)
    ctx["boundary_steps"] = int(ctx["boundary_steps"]) + 1
    hit_point = ctx["hit_point"]
    clear_line = not is_line_blocked(robot_pos, goal_pos, obstacles)
    closer_than_hit = False
    if isinstance(hit_point, tuple):
        closer_than_hit = euclidean(robot_pos, goal_pos) + 1e-9 < euclidean(hit_point, goal_pos)

    if clear_line and closer_than_hit:
        ctx["mode"] = "goto_goal"
        ctx["leave_point"] = robot_pos
        ctx["boundary_steps"] = 0
        LOGGER.info("Robot %s Bug2 mode switch: follow_boundary -> goto_goal", robot_id)
        return step_toward(robot_pos, goal_pos)

    if int(ctx["boundary_steps"]) >= CONFIG.boundary_fail_steps:
        boundary_start = ctx["boundary_start"]
        if isinstance(boundary_start, tuple) and euclidean(robot_pos, boundary_start) <= 1.0:
            ctx["bug2_failed"] = True
            LOGGER.warning("Robot %s Bug2 full-circuit failure detected", robot_id)

    return next_pos
