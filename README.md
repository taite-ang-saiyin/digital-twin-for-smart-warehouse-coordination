Project Overview

This module implements the **Environment and Core Simulation Engine** for a Smart Warehouse Digital Twin system.

It provides:

* 2D warehouse grid representation
* Topological graph generation
* Global world state management
* Deterministic time-step simulation engine
* Conflict resolution between robots
* Event-based logging and replay system

This serves as the foundational layer for higher-level modules such as task allocation and path planning.

---
System Architecture

```
warehouse_sim/
│
├── main.py
│
├── env/
│   ├── grid.py        # 2D warehouse grid
│   ├── graph.py       # Grid → Topological graph
│   └── state.py       # Global world state
│
└── sim/
    ├── engine.py      # Simulation loop
    ├── logger.py      # Event logging (JSONL)
    └── replay.py      # Replay tool
```

---
Features Implemented

Warehouse Grid

* 2D grid (ASCII-based loader)
* Cell types:

  * FREE
  * SHELF (obstacle)
  * PACKING STATION
  * CHARGING STATION
  * DEPOT

---
Topological Graph

* Junction detection
* Station/depot nodes
* Corridor edge tracing
* Weighted adjacency list
* Nearest node lookup

---
Global State Management

Tracks:

* Robot states (position, status, path, battery)
* Station occupancy
* Items (location, status)
* Dynamic obstacles (with TTL)

Provides clean APIs:

* `get_graph()`
* `is_cell_free()`
* `update_robot_position()`
* `set_robot_path()`
* `claim_station()`
* `release_station()`
* `add_dynamic_obstacle()`

---
Simulation Engine

Deterministic time-stepped loop:

Each tick:

1. Expire dynamic obstacles
2. Collect robot move intentions
3. Resolve target conflicts
4. Prevent swap conflicts
5. Apply validated moves
6. Update robot status
7. Log events

Conflict resolution:

* Priority by robot ID
* Swap detection implemented
* Deterministic execution order

---
Event Logging

Event-sourced logging system:

Logged events:

* `TICK_START`
* `ROBOT_MOVE`
* `ROBOT_WAIT`
* `STATION_CLAIM`
* `STATION_RELEASE`
* `DYN_OBS_ADD`
* `DYN_OBS_EXPIRE`

Output file:

```
events.jsonl
```

---
Replay System

Replay tool to inspect event log:

```bash
python -c "from sim.replay import replay_print; replay_print('events.jsonl')"
```

---
Requirements

Python 3.9+

No external dependencies required.

---
Run Simulation

From project root:

```bash
python main.py
```

This will:

* Build warehouse
* Generate topological graph
* Spawn robots
* Execute 10 simulation steps
* Generate `events.jsonl`

---
Design Decisions

* Single-threaded deterministic engine for reproducibility
* Event-sourced logging for debugging and replay
* Modular separation of environment, state, and simulation logic
* No global variables used
* Clear API boundaries for integration with other team modules
