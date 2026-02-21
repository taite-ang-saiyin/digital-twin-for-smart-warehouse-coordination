from __future__ import annotations

from env.grid import Grid
from env.graph import build_topological_graph
from env.state import WorldState, RobotState, StationState
from sim.engine import SimulationEngine
from sim.logger import EventLogger


def main() -> None:
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
    graph = build_topological_graph(grid)

    world = WorldState(grid=grid, graph=graph)

    # Stations (entrance is the station cell itself in this simple model)
    # (Find them by scanning grid, but we hardcode for demo)
    world.stations["pack_1"] = StationState(station_id="pack_1", kind="PACK", entrance=(10, 2))
    world.stations["charge_1"] = StationState(station_id="charge_1", kind="CHARGE", entrance=(16, 7))

    # Robots
    world.robots["r1"] = RobotState(robot_id="r1", pos=(1, 1))
    world.robots["r2"] = RobotState(robot_id="r2", pos=(2, 1))

    # Simple paths (grid cells)
    world.set_robot_path("r1", [(2, 1), (3, 1), (4, 1), (5, 1)])
    world.set_robot_path("r2", [(3, 1), (4, 1), (5, 1)])

    logger = EventLogger("events.jsonl", enabled=True)
    engine = SimulationEngine(world=world, logger=logger)

    engine.run(steps=10)

    print("Done. See events.jsonl")


if __name__ == "__main__":
    main()