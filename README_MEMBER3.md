# Member 3 Path Planning Module

## What this module includes

- Topological graph data structure (`Graph`) with node coordinates and weighted edges.
- Environment stub (`EnvironmentStub`) with:
  - `get_graph()`
  - `is_obstacle(x, y)` (currently always `False`)
  - `get_node_from_position(x, y)` (nearest-node lookup)
- Global planning:
  - Dijkstra (`dijkstra_shortest_path`) for baseline testing
  - A* (`shortest_path`) for primary planner
  - Non-node goal handling via temporary goal node attachment
- Local avoidance:
  - Bug2-style state machine (`bug2_step`) with per-robot persistent state
- Integrated planner API:
  - `get_next_move(robot_id)` for simulation loop usage
  - Uses stubs for robot position, sensor, and scheduler goal
- Replanning triggers:
  - Goal changed
  - Stagnation detected
  - Forced by external modules (`force_replan(robot_id)`)
  - Significant deviation from cached global path
- Optimization:
  - Global path cache (A* result caching by graph version/start/goal)
- Logging:
  - Info/debug events for replans, mode switches, and failures

## Main files

- `member3/graph.py`: graph data model + Dijkstra + utility functions.
- `member3/environment.py`: environment stub and environment setter/getter.
- `member3/avoidance.py`: Bug2-style local avoidance helpers.
- `member3/planner.py`: A*, replanning logic, and `get_next_move(robot_id)`.
- `member3/interfaces.py`: integration stubs for robot state/sensor/goal providers.
- `member3/tests.py`: prompt-by-prompt test helpers.
- `member3_planner.py`: compatibility wrapper (re-exports package API).
- `demo_member3.py`: full multi-robot demo with dynamic obstacles and metrics.

## Quick usage

Run prompt-level tests:

```bash
python member3_planner.py
```

Run full demo:

```bash
python demo_member3.py
```

## Integration points with other members

The final-facing API already follows integration style:

- `get_next_move(robot_id)`

Current stubs to replace later:

- `get_robot_position(robot_id)` -> replace with Member 2 robot state
- `get_robot_sensor(robot_id)` -> replace with Member 2 sensor stream
- `get_current_goal(robot_id)` -> replace with Member 4 scheduler output
- `ENV`/`EnvironmentStub` -> replace with Member 1 environment graph and queries

## Notes

- The module is self-contained and runnable without external dependencies.
- All planners use Euclidean distances based on node coordinates.
- Bug2 implementation is intentionally simplified for integration readiness and iterative refinement.
