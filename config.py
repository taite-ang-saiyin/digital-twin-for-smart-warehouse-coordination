from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    # Grid
    grid_w: int = 20
    grid_h: int = 20

    # GUI
    cell_px: int = 30
    margin_px: int = 20
    fps: int = 10  # GUI update rate

    # Coordination
    reserve_mode: str = "cell"  # cell reservation only
    max_wait_before_replan: int = 25
    deadlock_window: int = 20
    backoff_steps: int = 8

    # Logging
    log_dir: str = "logs"
    csv_name: str = "metrics.csv"
    csv_every_steps: int = 10

CFG = Config()