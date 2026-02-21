import heapq
import math
from typing import Dict, List, Optional, Tuple

from .types import NodeId, Point


class Graph:
    def __init__(self) -> None:
        self.nodes: Dict[NodeId, Point] = {}
        self.edges: Dict[NodeId, List[Tuple[NodeId, float]]] = {}
        self.version: int = 0

    def add_node(self, node_id: NodeId, x: float, y: float) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = (float(x), float(y))
            self.edges[node_id] = []
            self.version += 1
            return
        self.nodes[node_id] = (float(x), float(y))

    def add_edge(
        self,
        source: NodeId,
        target: NodeId,
        weight: float,
        bidirectional: bool = True,
    ) -> None:
        self.edges.setdefault(source, [])
        self.edges.setdefault(target, [])
        self.edges[source].append((target, float(weight)))
        if bidirectional:
            self.edges[target].append((source, float(weight)))
        self.version += 1

    def get_neighbors(self, node_id: NodeId) -> List[Tuple[NodeId, float]]:
        return self.edges.get(node_id, [])


def _node_id(x: int, y: int) -> NodeId:
    return f"n_{x}_{y}"


def euclidean(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def load_test_graph(width: int = 3, height: int = 3, spacing: float = 1.0) -> Graph:
    graph = Graph()
    for y in range(height):
        for x in range(width):
            graph.add_node(_node_id(x, y), x * spacing, y * spacing)

    for y in range(height):
        for x in range(width):
            current = _node_id(x, y)
            if x + 1 < width:
                graph.add_edge(current, _node_id(x + 1, y), spacing, bidirectional=True)
            if y + 1 < height:
                graph.add_edge(current, _node_id(x, y + 1), spacing, bidirectional=True)
    return graph


def print_adjacency_list(graph: Graph) -> None:
    print("Adjacency List:")
    for node_id in sorted(graph.nodes):
        neighbors = ", ".join(f"({nbr}, w={w:.2f})" for nbr, w in graph.get_neighbors(node_id))
        print(f"  {node_id}: {neighbors}")


def dijkstra_shortest_path(graph: Graph, start_node: NodeId, goal_node: NodeId) -> Tuple[Optional[List[NodeId]], float]:
    if start_node not in graph.nodes or goal_node not in graph.nodes:
        return None, math.inf

    queue: List[Tuple[float, NodeId]] = [(0.0, start_node)]
    distances: Dict[NodeId, float] = {start_node: 0.0}
    previous: Dict[NodeId, Optional[NodeId]] = {start_node: None}

    while queue:
        current_cost, current = heapq.heappop(queue)
        if current == goal_node:
            break
        if current_cost > distances.get(current, math.inf):
            continue
        for neighbor, weight in graph.get_neighbors(current):
            candidate = current_cost + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                previous[neighbor] = current
                heapq.heappush(queue, (candidate, neighbor))

    if goal_node not in distances:
        return None, math.inf

    path: List[NodeId] = []
    node: Optional[NodeId] = goal_node
    while node is not None:
        path.append(node)
        node = previous.get(node)
    path.reverse()
    return path, distances[goal_node]
