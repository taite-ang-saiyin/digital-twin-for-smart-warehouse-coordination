Digital Twin Warehouse Simulation – Team Roles & Responsibilities

Project: Digital Twin for Smart Warehouse Coordination
Team Size: 5 members
Duration: 10–12 weeks
Last Updated: [Insert Date]

---

1. Overview

This document defines the roles, responsibilities, and deliverables for each team member. The project is divided into six phases, with each member leading a specific module. Close collaboration and adherence to interfaces are essential for successful integration.

---

1. Team Roles Summary

Member Primary Module Key Deliverables Dependencies
Member 1 Environment & Core Simulation Engine – Warehouse layout (grid/topological graph) – Main simulation loop – APIs for world state None
Member 2 Robot Agent & Basic Movement – Robot class with properties and methods – Simulated sensors/actuators – Movement logic Environment (Member 1)
Member 3 Path Planning (Global + Local) – Dijkstra (or A*) global planner – Bug2 / potential field local avoidance – get_next_move() function Environment (Member 1), Robot positions (Member 2)
Member 4 Task Management & Scheduling – Task data structures – Random order generator – Central scheduler with resource constraints Environment (Member 1), Robot status (Member 2)
Member 5 Coordination & Visualization – Multi‑agent coordination (traffic, negotiation) – Real‑time GUI (e.g., pygame) – Metrics dashboard & logging All other modules

---

1. Detailed Responsibilities

Member 1 – Environment & Core Simulation Engine

· Design the warehouse:
· Create a 2D grid (e.g., 20×20) with cells representing free space, obstacles (shelves), stations (packing, charging), and depots.
· Convert grid into a topological graph: nodes at landmarks (junctions, station entrances) and edges representing traversable paths. Assign weights (distance or travel time) to edges.
· Maintain global state:
· Keep track of robot positions, station occupancy, item locations, and any dynamic obstacles.
· Provide clean APIs for other modules to query and update the world (e.g., get_graph(), is_cell_free(x,y), update_robot_position(robot_id, new_pos)).
· Implement the simulation loop:
· Time‑stepped or event‑based loop that updates robot actions, task progress, and resource states.
· Ensure thread‑safe access if using multiple threads (though a single‑threaded loop with sequential robot updates is simpler).
· Provide logging of all state changes for replay and debugging.

Member 2 – Robot Agent & Basic Movement

· Define the Robot class:
· Attributes: ID, position, orientation, battery level, task queue, status (IDLE, MOVING, PICKING, CHARGING, etc.).
· Simulate sensors:
· Provide methods like detect_obstacles(range) returning nearby obstacles or other robots.
· (Optional) Simulate landmark detection for topological navigation.
· Simulate actuators:
· Implement move(direction) that updates robot position (after checking with Member 1’s environment).
· Implement pick(item) and drop(item) actions (interacting with inventory).
· Implement charge() that occupies a charging station and restores battery over time.
· Expose robot status to other modules (position, battery, current task) through getter methods or a shared state.

Member 3 – Path Planning (Global + Local)

· Global path planning:
· Implement Dijkstra’s algorithm (or A* for efficiency) on the topological graph provided by Member 1.
· Given a robot’s current node and a goal node, return the shortest path as a list of waypoints/nodes.
· Handle cases where the goal is not a node (e.g., a shelf cell) by connecting to the nearest node.
· Local obstacle avoidance:
· Implement Bug2 algorithm or a potential field method to navigate around unexpected dynamic obstacles (e.g., other robots, temporary blockages).
· Integrate with global planner: if local avoidance deviates significantly from the global path, trigger a replan.
· Provide a function get_next_move(robot_id, goal) that returns the immediate next direction or waypoint for the robot to move.
· Optimise replanning frequency to avoid excessive computation.

Member 4 – Task Management & Scheduling

· Define task structures:
· Each task has: type (MOVE, PICK, DROP, CHARGE), required resources (e.g., station ID), estimated duration, deadline (optional), and associated location.
· Create an order generator:
· Randomly generate orders (e.g., “pick item X from shelf S and deliver to station P”) to simulate incoming work.
· Implement a central scheduler:
· Assign tasks to robots based on a heuristic (e.g., greedy: nearest idle robot, earliest deadline, shortest processing time).
· Manage resource constraints: ensure that tasks requiring a specific station (packing, charging) are not assigned if the station is occupied.
· Maintain a queue of pending tasks and update robot task lists.
· Provide APIs for robots to request new tasks and report task completion.

Member 5 – Coordination & Visualization

· Multi‑agent coordination:
· Implement traffic rules to prevent collisions (e.g., robots reserve the next edge before moving; if reservation fails, they wait or reroute).
· Add deadlock detection (e.g., cycles of waiting robots) and resolution (e.g., one robot backs off).
· (Optional) Implement a simple negotiation protocol for shared resources (e.g., robots bid for charging station based on battery level).
· Graphical user interface:
· Develop a real‑time visualisation (using pygame, tkinter, or a web framework) that shows:
· Warehouse grid, obstacles, stations.
· Robots as icons with ID and status.
· Current paths (if desired).
· Task assignments and resource queues.
· Ensure the GUI updates smoothly without blocking the simulation.
· Metrics dashboard:
· Display live statistics: average order completion time, robot utilisation, energy consumption, number of conflicts resolved.
· Log data to CSV for post‑run analysis (e.g., completion time vs. number of robots).
· Integrate all modules by calling their APIs and passing information between them.

---

1. Communication & Integration Plan

· Weekly meetings (30 min) to synchronise progress, discuss interface changes, and resolve blockers.
· Shared repository (Git/GitHub) with a branching strategy (e.g., each member works on a feature branch; merge into develop every week).
· Interface contract document (this document plus a separate API specification) that defines all function signatures, data structures, and expected behaviours. Update it as needed.
· Milestone integration every two weeks: merge all branches and run integration tests. Use stubs where dependencies are not yet ready.
· Issue tracking (GitHub Issues or Trello) to manage tasks and bugs.

---

1. Timeline & Milestones

Week Focus Integration Milestone
1–2 Environment, basic robot, dummy path, dummy scheduler, basic GUI Skeleton with grid and moving robot (hardcoded path)
3–4 Dijkstra global planner, task generator, improved GUI Robot moves using Dijkstra to assigned tasks
5–7 Local avoidance, resource‑aware scheduler, traffic rules Full simulation with multiple robots, basic coordination
8–10 Advanced features (negotiation, replanning, metrics) Stable system with dashboard
11–12 Testing, experiments, report writing Final demo and report

---

1. Final Deliverables

· Complete source code with documentation.
· A short user manual / README.
· Final report covering:
· Problem definition and approach.
· Algorithms used (with references to lecture topics).
· Experimental results (graphs, analysis).
· Individual contributions.
· A demonstration video (optional).