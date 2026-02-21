from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Literal, Tuple

Cell = Literal[
    "FREE",
    "SHELF",
    "STATION_PACK",
    "STATION_CHARGE",
    "DEPOT",
    "DYN_BLOCK",
]

TRAVERSABLE = {"FREE", "STATION_PACK", "STATION_CHARGE", "DEPOT"}  # DYN_BLOCK handled separately


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    cells: List[List[Cell]]  # cells[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def cell_type(self, x: int, y: int) -> Cell:
        if not self.in_bounds(x, y):
            raise IndexError(f"Out of bounds: {(x, y)}")
        return self.cells[y][x]

    def is_static_free(self, x: int, y: int) -> bool:
        """Traversable ignoring robots and dynamic obstacles."""
        return self.in_bounds(x, y) and self.cells[y][x] in TRAVERSABLE

    def neighbors4(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield (nx, ny)

    @staticmethod
    def from_ascii(lines: List[str]) -> "Grid":
        """
        Simple loader:
          '.' = FREE
          '#' = SHELF
          'P' = STATION_PACK
          'C' = STATION_CHARGE
          'D' = DEPOT
        """
        if not lines:
            raise ValueError("No lines provided")

        height = len(lines)
        width = len(lines[0])
        for line in lines:
            if len(line) != width:
                raise ValueError("All lines must have same width")

        mapping = {
            ".": "FREE",
            "#": "SHELF",
            "P": "STATION_PACK",
            "C": "STATION_CHARGE",
            "D": "DEPOT",
        }

        cells: List[List[Cell]] = []
        for y in range(height):
            row: List[Cell] = []
            for x in range(width):
                ch = lines[y][x]
                if ch not in mapping:
                    raise ValueError(f"Unknown char '{ch}' at {(x,y)}")
                row.append(mapping[ch])  # type: ignore[arg-type]
            cells.append(row)

        return Grid(width=width, height=height, cells=cells)