from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import itertools
import random

from .interfaces import Pos, StationId, ItemId
from .models import Order


@dataclass
class Catalog:
    shelf_positions: List[Pos]
    packing_stations: Dict[StationId, Pos]
    item_ids: List[ItemId]


class OrderGenerator:
    def __init__(
        self,
        catalog: Catalog,
        *,
        p_new_order: float = 0.10,
        deadline_range: Tuple[int, int] = (80, 200),
        seed: Optional[int] = None,
    ):
        self.catalog = catalog
        self.p_new_order = p_new_order
        self.deadline_range = deadline_range
        self.rng = random.Random(seed)
        self._oid = itertools.count(1)

    def maybe_generate(self, tick: int) -> Optional[Order]:
        if self.rng.random() > self.p_new_order:
            return None

        oid = next(self._oid)
        item = self.rng.choice(self.catalog.item_ids)
        shelf = self.rng.choice(self.catalog.shelf_positions)
        pack_id = self.rng.choice(list(self.catalog.packing_stations.keys()))
        pack_pos = self.catalog.packing_stations[pack_id]
        ddl = tick + self.rng.randint(*self.deadline_range)

        return Order(
            id=oid,
            item_id=item,
            shelf_pos=shelf,
            pack_station_id=pack_id,
            pack_station_pos=pack_pos,
            created_tick=tick,
            deadline_tick=ddl,
        )