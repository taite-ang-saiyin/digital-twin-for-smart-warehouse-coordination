import logging
from dataclasses import dataclass
from typing import Optional


LOGGER = logging.getLogger("member3_planner")


@dataclass
class PlannerConfig:
    enable_cache: bool = True
    cache_size: int = 512
    log_level: int = logging.INFO
    deviation_threshold: float = 2.0
    stagnation_distance: float = 0.1
    stagnation_steps: int = 10
    step_size: float = 1.0
    boundary_fail_steps: int = 80


CONFIG = PlannerConfig()


def configure_planner(
    enable_cache: Optional[bool] = None,
    cache_size: Optional[int] = None,
    log_level: Optional[int] = None,
) -> None:
    if enable_cache is not None:
        CONFIG.enable_cache = enable_cache
    if cache_size is not None:
        CONFIG.cache_size = cache_size
    if log_level is not None:
        CONFIG.log_level = log_level

    logging.basicConfig(
        level=CONFIG.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    LOGGER.setLevel(CONFIG.log_level)
