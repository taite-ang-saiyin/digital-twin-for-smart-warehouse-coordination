Prompt 1 – Data Structures & Environment Stub

```
We are building a path planning module for a warehouse robot simulation. The environment is represented as a topological graph (nodes = landmarks, edges = navigable paths with weights). Please create the following:

1. A class `Graph` that stores:
   - nodes: a dictionary mapping node_id -> (x, y) coordinates.
   - edges: a dictionary mapping node_id -> list of (neighbor_id, weight) tuples.
   Provide methods to add nodes and edges, and to get neighbors.

2. A function `load_test_graph()` that returns a simple test graph (e.g., a 3x3 grid of nodes with unit edge weights). The nodes should have coordinates for visualization later.

3. A stub for the environment (to be replaced by Member 1's code later) that provides:
   - `get_graph()` returning the Graph object.
   - `is_obstacle(x, y)` returning False for now (no static obstacles).
   - `get_node_from_position(x, y)` returning the nearest node ID (implement a simple Euclidean distance search).

Write the code with clear comments and include a small test that prints the graph's adjacency list.
```

---

Prompt 2 – Dijkstra’s Algorithm

```
Now implement Dijkstra's shortest path algorithm for the Graph class.

Write a function `shortest_path(graph, start_node, goal_node)` that:
- Takes a Graph object, a start node ID, and a goal node ID.
- Returns a tuple: (path_list, total_cost), where path_list is a list of node IDs from start to goal (inclusive). If no path exists, return (None, inf).
- Use a priority queue (heapq) for efficiency.

Add a test that finds the path between two nodes in the test graph and prints the result.
```

---

Prompt 3 – Basic get_next_move (Global Only)

```
Create the main API function `get_next_move(robot_id, goal, robot_pos)` that will be called every simulation step. For now, it only uses global planning.

Specifications:
- `robot_id` is an integer (unused for now, but may be needed later).
- `goal` can be a node ID or an (x, y) tuple. If it's an (x, y) tuple, convert it to the nearest node using `get_node_from_position`.
- `robot_pos` is an (x, y) tuple of the robot's current position. Convert it to the nearest start node.
- Call `shortest_path` to get the full path.
- If the path has at least 2 nodes, return the next node's coordinates (as an (x, y) tuple) – the step the robot should take. If the path has only one node (already at goal), return None.

Use the environment stubs from Prompt 1. Write a small test that simulates a robot moving step by step from (0,0) to (2,2) on the test graph, printing each next move.
```

---

Prompt 4 – A Enhancement & Non‑Node Goals*

```
Improve the global planner:

1. Replace Dijkstra with A* for better performance. Use Euclidean distance as the heuristic (based on node coordinates). Keep the same function signature `shortest_path(graph, start, goal)` – you can add a heuristic parameter.

2. Extend the function to handle goals that are not exactly nodes. If `goal` is an (x,y) coordinate:
   - Create a temporary node with that coordinate.
   - Connect it to the nearest permanent node with an edge weight equal to the Euclidean distance.
   - Run A* from start to this temporary node, then discard the temporary node.
   - Return the path excluding the temporary node.

Update `get_next_move` accordingly. Test with a goal coordinate not exactly on a node.
```

---

Prompt 5 – Local Obstacle Avoidance: Bug2 Basics

```
Now we add local obstacle avoidance using the Bug2 algorithm. The robot has a simulated short‑range sensor that returns a set of points (cells) that are occupied within a radius.

First, create a sensor stub (to be replaced by Member 2's code later):
- `detect_obstacles(robot_id, robot_pos, radius=2.0)` returns a list of (x, y) tuples representing occupied cells (for now, generate a few dummy obstacles near the robot's path).

Implement the Bug2 algorithm with the following states stored per robot (use a dictionary `robot_state` that persists between calls):
- `mode`: "goto_goal" or "follow_boundary"
- `hit_point`: (x, y) where obstacle first encountered
- `leave_point`: (x, y) where we can leave the boundary (the point on the obstacle boundary that lies on the line from hit_point to goal)

Write a function `bug2_step(robot_pos, goal_pos, obstacles)` that:
- If mode == "goto_goal":
   - Compute direction toward goal.
   - If the straight line to goal is blocked by any obstacle (check if any obstacle lies on the line segment), switch to "follow_boundary", record hit_point = robot_pos, and start following the obstacle boundary clockwise.
   - Else return the direction as a unit step (dx, dy) toward goal.
- If mode == "follow_boundary":
   - Move along the obstacle boundary (simulate by turning right relative to the obstacle normal). You can implement a simple boundary follower: try to move in a direction that keeps the obstacle on the left (clockwise) while not moving into obstacles.
   - Every step, check if the line from the current position to goal is clear AND we are at a point that is closer to goal than the hit_point (or on the m‑line). If so, switch back to "goto_goal".
   - Return the next step.

For now, use a very simplified boundary following: if you have a set of occupied cells, you can simulate following by moving in a direction that is 90 degrees left from the vector pointing to the nearest obstacle. We'll refine later.

Test with a simple scenario: robot at (0,0), goal at (5,0), and an obstacle at (2,0) blocking the direct path. Simulate a few steps.
```

---

Prompt 6 – Integrate Bug2 with Global Path Following

```
Modify `get_next_move` to incorporate local avoidance:

- The function now also receives `sensor_data` (the list of obstacles from the stub) and maintains a persistent `robot_context` dictionary that stores the current Bug2 state (mode, hit_point, leave_point, etc.) for each robot.
- The global path (from A*) is used as a series of waypoints. However, local avoidance may cause the robot to deviate. We still need to know the next global waypoint as the sub‑goal.
- Logic:
   - Get the global path from robot's current position to the ultimate goal (using A*). The first waypoint on that path (excluding current position) is the immediate sub‑goal.
   - If no obstacles are detected on the direct line to that sub‑goal, move toward it (using simple step‑toward).
   - If obstacles are detected, invoke Bug2 with the sub‑goal as the target.
   - If Bug2 completes (reaches the sub‑goal), reset mode to "goto_goal" and get the next sub‑goal.
- If the robot deviates significantly from the global path (e.g., distance to path > threshold), replan the global path from current position.

Implement this integration. Use a threshold of 2.0 cells. Test with a scenario where a dynamic obstacle appears on the planned path.
```

---

Prompt 7 – Replanning Triggers

```
Add replanning triggers to `get_next_move`:

- Replan if the robot has not made progress for a certain number of steps (e.g., position change < 0.1 for 10 steps) – this indicates being stuck.
- Replan if the goal changes (this will be handled by the scheduler later, but we can add a check that if the goal passed to `get_next_move` is different from the last goal, we replan).
- Replan if the global path becomes completely blocked and Bug2 cannot find a way (e.g., after a full circuit of an obstacle, we realize the goal is unreachable – then we should notify the scheduler).

Store the last goal and last path for each robot. Provide a function `force_replan(robot_id)` that can be called by other modules (e.g., coordination) to request a new plan.

Add a simple counter for stagnation and test by placing a robot in a dead‑end.
```

---

Prompt 8 – Optimisation & Logging

```
Optimise the module:

- Cache A* results for the same (start, goal) pair if the graph hasn't changed (the graph is static for now). Use an LRU cache or simple dictionary.
- In `get_next_move`, avoid recomputing the global path every step if the robot is still following it and hasn't deviated.
- Add logging (using Python's `logging` module) to record path planning events, replans, mode switches, etc. Use different log levels (DEBUG for details, INFO for major events).

Provide a configuration option to enable/disable caching and set log level.

Test with multiple robots to ensure caching doesn't interfere (use robot_id in cache key if needed).
```

---

Prompt 9 – Integration Stubs for Other Modules

```
To make the module ready for integration with the rest of the team, create stub interfaces for the functions that will be provided by other members:

- `get_robot_position(robot_id)`: stub that returns a position from a hardcoded dictionary (to be replaced by Member 2's actual function).
- `get_robot_sensor(robot_id)`: stub that returns obstacle list (as before).
- `get_current_goal(robot_id)`: stub that returns a goal (node or coordinate) from a simple task list (to be replaced by Member 4).

Modify `get_next_move` to use these stubs instead of taking parameters directly. The function signature becomes `get_next_move(robot_id)`. This is how it will be called in the final simulation loop.

Write a small simulation loop that updates each robot sequentially, calling `get_next_move` and printing the result.
```

---

Prompt 10 – Final Testing & Demo Script

```
Create a comprehensive test script that demonstrates all features:

- A larger test environment (e.g., a 10x10 grid with several obstacles).
- Multiple robots with different goals.
- Introduce dynamic obstacles that appear/disappear.
- Show logging output.
- Measure and print performance metrics: average planning time per call, number of replans, path length vs. straight‑line distance.

The script should be self‑contained and use only the stubs, so it can be run immediately.

Also write a brief README explaining the module's API, algorithms used, and how to integrate with the other team members' code.
```
