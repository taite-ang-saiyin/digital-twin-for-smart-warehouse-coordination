from typing import Optional

from .graph import Graph, euclidean, load_test_graph
from .types import NodeId


class EnvironmentStub:
    def __init__(self, graph: Optional[Graph] = None) -> None:
        self._graph = graph if graph is not None else load_test_graph()

    def get_graph(self) -> Graph:
        return self._graph

    def is_obstacle(self, x: float, y: float) -> bool:
        _ = (x, y)
        return False

    def get_node_from_position(self, x: float, y: float) -> NodeId:
        query = (float(x), float(y))
        nearest = min(self._graph.nodes, key=lambda node_id: euclidean(self._graph.nodes[node_id], query))
        return nearest


ENV = EnvironmentStub()


def get_environment() -> EnvironmentStub:
    return ENV


def set_environment(environment: EnvironmentStub) -> None:
    global ENV
    ENV = environment
