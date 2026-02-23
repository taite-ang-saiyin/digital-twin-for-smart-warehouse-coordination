# Integrated Member 1/2/3/5 Setup

This repository now includes `integrated_run.py`, which combines:

- `Member 1`: environment/grid/topological graph/world state + event logging
- `Member 2`: robot agents (`Robot`, `RobotFactory`)
- `Member 3`: path planning core (`shortest_path` / A*)
- `Member 5`: coordination (`TrafficCoordinator`) + metrics (optional GUI with `--gui`)

## Notes (matches `PROJECT.md`)

- `Member 4` (scheduler) is not included, so `integrated_run.py` uses a small placeholder scheduler to keep the integrated loop runnable.
- Member 3 planning is used through an adapter that converts Member 1's topological graph into a Member 3 graph and expands planned node paths into grid-cell steps for Member 2/5 execution.
- Member 5 GUI is optional and disabled by default for compatibility with headless environments.

## Run

```bash
python integrated_run.py --steps 50
```

Optional GUI:

```bash
python integrated_run.py --steps 200 --gui --sleep 0.05
```

## Outputs

- `integrated_output/events.jsonl` (Member 1-style event log)
- `integrated_output/metrics.csv` (Member 5 metrics log)
