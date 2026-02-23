# Digital Twin Warehouse (Integrated Run)

This repo contains an integrated runnable setup for:

- `Member 1` (environment + world state + event logging)
- `Member 2` (robot agents)
- `Member 3` (path planning)
- `Member 5` (coordination + metrics + optional GUI)

The integration entry point is `integrated_run.py`.

## Prerequisites

- Python `3.9+` (tested locally with a newer Python version as well)
- No extra packages required for headless mode
- Tkinter available (only if using `--gui`)

## How to Run

Headless (recommended first run):

```bash
python integrated_run.py --steps 50
```

With Member 5 GUI (Tkinter):

```bash
python integrated_run.py --steps 200 --gui --sleep 0.05
```

## What the Run Does

- Builds a warehouse world from Member 1 grid/topology
- Creates Member 2 robots
- Uses Member 3 path planning via an adapter
- Uses Member 5 traffic coordination + deadlock handling + metrics logging
- Runs a simulation loop for the number of steps you pass

## Output Files

Generated in `integrated_output/`:

- `events.jsonl` (Member 1-style event log)
- `metrics.csv` (Member 5 metrics log)

## CLI Options

- `--steps <int>`: number of simulation steps (default: `50`)
- `--gui`: enable Tkinter visualization
- `--sleep <seconds>`: delay per step (useful with GUI)

## Important Note

- `Member 4` is not included in this integration yet, so `integrated_run.py` uses a simple placeholder scheduler to keep the system runnable.

## References

- `PROJECT.md` for team responsibilities and integration plan
- `INTEGRATION.md` for the integration-specific summary
