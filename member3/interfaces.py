from typing import Dict, List

from .graph import euclidean
from .types import GoalType, Point


ROBOT_POSITIONS: Dict[int, Point] = {
    1: (0.0, 0.0),
    2: (0.0, 2.0),
    3: (2.0, 0.0),
}

ROBOT_GOALS: Dict[int, GoalType] = {
    1: (2.0, 2.0),
    2: "n_2_0",
    3: (0.0, 2.0),
}

DYNAMIC_OBSTACLES: List[Point] = []


def get_robot_position(robot_id: int) -> Point:
    return ROBOT_POSITIONS[robot_id]


def set_robot_position(robot_id: int, pos: Point) -> None:
    ROBOT_POSITIONS[robot_id] = (float(pos[0]), float(pos[1]))


def detect_obstacles(
    robot_id: int,
    robot_pos: Point,
    radius: float = 2.0,
    use_dummy: bool = False,
) -> List[Point]:
    _ = robot_id
    visible = [point for point in DYNAMIC_OBSTACLES if euclidean(point, robot_pos) <= radius]
    if visible:
        return visible
    if use_dummy:
        return [(robot_pos[0] + 2.0, robot_pos[1])]
    return []


def get_robot_sensor(robot_id: int) -> List[Point]:
    return detect_obstacles(robot_id, get_robot_position(robot_id), radius=3.5, use_dummy=False)


def get_current_goal(robot_id: int) -> GoalType:
    return ROBOT_GOALS[robot_id]
