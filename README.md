(Member 5)

### ✅ Multi-Agent Coordination

* Cell reservation system (traffic rule)
* Conflict detection
* Deadlock detection
* Deadlock resolution via backoff mechanism

### ✅ Real-Time Visualization (Tkinter)

* 2D warehouse grid
* Obstacles (shelves)
* Stations (packing & charging)
* Robots with:

  * ID
  * Status (MOVING / WAITING / BACKOFF / IDLE)
  * Optional path visualization

### ✅ Metrics Dashboard

Live statistics:

* Simulation step count
* Total moved steps
* Total waited steps
* Conflicts resolved
* Deadlocks resolved

### ✅ CSV Logging

Logs to:

```
logs/metrics.csv
```

For post-run analysis.

---

# 🗂 Project Structure

```
member5_tkinter/
│
├── main.py              # Simulation loop + integration point
├── config.py            # Configuration parameters
├── interfaces.py        # Integration APIs for other members
├── coordinator.py       # Traffic + reservation logic
├── deadlock.py          # Deadlock detection & resolution
├── metrics.py           # Metrics tracking + CSV logging
├── gui_tk.py            # Tkinter visualization
├── demo_world.py        # Temporary demo environment (replace later)
│
└── logs/
```

---

# ▶ How to Run

### 1️⃣ Requirements

* Python 3.9+
* No external libraries required (Tkinter is built-in)

### 2️⃣ Run

```bash
python main.py
```

A Tkinter window will open with the simulation.

---

# 🔄 Integration With Other Members

Currently, `demo_world.py` provides stub implementations.

To integrate with the full project:

### Replace in `main.py`:

```python
env, planner, scheduler = build_demo()
```

with:

```python
env = RealEnvironment()      # Member 1
planner = RealPlanner()      # Member 3
scheduler = RealScheduler()  # Member 4
```

No other changes required.

The coordination and GUI layer remains unchanged.

---

# 🧠 Coordination Logic Overview

### Reservation Rule

A robot may move into a cell only if:

* The cell is not blocked
* The cell is not reserved by another robot

### Deadlock Detection

If multiple robots:

* Have not made progress for `deadlock_window` steps
* Are waiting on each other

Then:

* A victim robot is selected
* It enters BACKOFF state for several steps
* Deadlock is resolved

---

# 📊 Metrics Logged

CSV format:

```
time_s, step, robots,
moved_total, waited_total,
conflicts_resolved, deadlocks_resolved
```

---

# 🎯 Design Goals

* Fully Python-based for clean integration
* No external simulation software
* Modular architecture
* Easy to merge with main project
* Clear separation of responsibilities

---

# 📌 Notes

* The GUI runs in the same simulation loop (single-threaded)
* Safe for integration with sequential robot updates
* Designed to work with 3–10 robots
* Grid size configurable in `config.py`

---

# 👨‍💻 Member 5 Contribution

This module provides:

* Traffic coordination system
* Deadlock detection
* Visualization layer
* Metrics dashboard
* Integration orchestration

---



**Ready for GitHub push.**
