from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .grid import Grid

NodeId = int


@dataclass(frozen=True)
class Node:
    id: NodeId
    x: int
    y: int
    kind: str  # "JUNCTION" | "STATION" | "DEPOT" | etc.


@dataclass
class TopoGraph:
    nodes: Dict[NodeId, Node]
    pos_to_node: Dict[Tuple[int, int], NodeId]
    adj: Dict[NodeId, List[Tuple[NodeId, float]]]  # neighbor, weight

    def nearest_node_id(self, x: int, y: int) -> Optional[NodeId]:
        return self.pos_to_node.get((x, y))


def _is_landmark(grid: Grid, x: int, y: int) -> bool:
    ct = grid.cell_type(x, y)
    if ct in ("STATION_PACK", "STATION_CHARGE", "DEPOT"):
        return True

    if not grid.is_static_free(x, y):
        return False

    # Count traversable neighbors
    neigh = [(nx, ny) for (nx, ny) in grid.neighbors4(x, y) if grid.is_static_free(nx, ny)]
    deg = len(neigh)
    if deg != 2:
        return True

    # deg == 2: node if not straight (corner)
    (x1, y1), (x2, y2) = neigh
    # Straight if both neighbors share x or both share y with current
    straight = (x1 == x == x2) or (y1 == y == y2)
    return not straight


def build_topological_graph(grid: Grid) -> TopoGraph:
    # 1) create nodes
    nodes: Dict[NodeId, Node] = {}
    pos_to_node: Dict[Tuple[int, int], NodeId] = {}
    nid = 0
    for y in range(grid.height):
        for x in range(grid.width):
            if _is_landmark(grid, x, y):
                ct = grid.cell_type(x, y)
                if ct == "DEPOT":
                    kind = "DEPOT"
                elif ct in ("STATION_PACK", "STATION_CHARGE"):
                    kind = "STATION"
                else:
                    kind = "JUNCTION"
                nodes[nid] = Node(id=nid, x=x, y=y, kind=kind)
                pos_to_node[(x, y)] = nid
                nid += 1

    # 2) corridor tracing to add edges
    adj: Dict[NodeId, List[Tuple[NodeId, float]]] = {i: [] for i in nodes.keys()}

    def add_edge(a: NodeId, b: NodeId, w: float) -> None:
        # undirected, avoid duplicates
        if all(nb != b for nb, _ in adj[a]):
            adj[a].append((b, w))
        if all(na != a for na, _ in adj[b]):
            adj[b].append((a, w))

    # For each node, try 4 directions and trace until another node
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for a_id, a in nodes.items():
        for dx, dy in dirs:
            x, y = a.x + dx, a.y + dy
            dist = 1
            if not grid.in_bounds(x, y) or not grid.is_static_free(x, y):
                continue

            # Walk corridor until hitting landmark or dead end
            while True:
                if (x, y) in pos_to_node:
                    b_id = pos_to_node[(x, y)]
                    if b_id != a_id:
                        add_edge(a_id, b_id, float(dist))
                    break

                # continue straight if possible; corridor could branch but then we'd have a node already
                nx, ny = x + dx, y + dy
                if not grid.in_bounds(nx, ny) or not grid.is_static_free(nx, ny):
                    break
                x, y = nx, ny
                dist += 1

    return TopoGraph(nodes=nodes, pos_to_node=pos_to_node, adj=adj)