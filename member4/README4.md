# Member 4 -- Task Management & Scheduling

## Overview

Member 4 implements the **Task Management and Scheduling module** for
the warehouse robotics system.

This module is responsible for:

-   Generating customer orders\
-   Converting orders into executable task chains\
-   Assigning tasks to robots using a scheduling heuristic\
-   Managing shared resource constraints (packing and charging
    stations)\
-   Tracking task and order completion

This implementation is designed to be **standalone** and communicates
with other members' components strictly through `interfaces.py`.

------------------------------------------------------------------------

## Core Responsibility

Member 4 decides:

> **WHAT work each robot should do next.**

It does **not** decide: - How a robot moves (Member 3 -- Path
Planning) - How collisions are avoided (Member 5 -- Coordination) - How
the world grid updates (Member 1 -- Environment) - How robot motion is
executed (Member 2 -- Robot Agent)

------------------------------------------------------------------------

## System Architecture

    Member 4 (Scheduler) → Member 2 (Robot) → Member 3 (Planner)
                                         ↓
                                   Member 5 (Coordination)
                                         ↓
                                   Member 1 (Environment)

------------------------------------------------------------------------

## What Member 4 Outputs

Member 4 outputs **task assignments**.

Tasks are sent to robots using:

``` python
IRobotAgent.assign_task(task_dict)
```

Example task formats:

### MOVE

``` python
{"type": "MOVE", "location": (x, y)}
```

### PICK

``` python
{"type": "PICK", "item_id": "SKU3", "item_location": (x, y)}
```

### DROP

``` python
{"type": "DROP", "item_id": "SKU3", "station_id": "P1", "station_location": (x, y)}
```

### CHARGE

``` python
{"type": "CHARGE", "station_id": "C1", "station_location": (x, y)}
```

Member 4 does **not** produce: - Movement steps (UP/DOWN/LEFT/RIGHT) -
Path waypoints - Collision resolutions - Grid updates

------------------------------------------------------------------------

## Module Structure

    member4/
    │
    ├── interfaces.py
    ├── models.py
    ├── order_generator.py
    ├── scheduler.py
    ├── adapters_mock.py
    ├── demo_main.py
    └── README.md

------------------------------------------------------------------------

## Scheduling Strategy

The scheduler uses a heuristic based on:

-   Robot utility score\
-   Distance to task location\
-   Deadline urgency (if defined)\
-   Battery level (low battery → prioritize charging)\
-   Station availability (no double-booking)

Optional enhancements when integrated: - Use Member 3 planner cost
instead of Manhattan distance\
- Use Member 5 congestion hints

------------------------------------------------------------------------

## Running Standalone

From repository root:

``` bash
python -m member4.demo_main
```

The demo verifies:

-   Task creation\
-   Scheduling correctness\
-   Resource locking\
-   Order completion

------------------------------------------------------------------------

## Integration Plan

### Member 1 (Environment)

Implement `IWorldState`: - current_tick() - claim_station() -
release_station() - station queries

### Member 2 (Robot)

Implement `IRobotAgent`: - get_snapshot() - assign_task() -
calculate_utility()

### Member 3 (Optional)

Implement `IPathPlanner` to improve scheduling accuracy.

### Member 5 (Optional)

Implement `ICoordinator` for congestion-aware scheduling.

------------------------------------------------------------------------

## Design Principles

-   Strict separation of concerns\
-   Interface-driven architecture\
-   No direct imports from other members\
-   Easily testable standalone\
-   Merge-ready with minimal changes

------------------------------------------------------------------------




