"""
tiny_graph.py — Zero-dependency in-memory property graph for Python.
"""


from __future__ import annotations

__version__ = "0.1.0"
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

@dataclass
class Node:
    id: str
    labels: set[str] = field(default_factory=set)
    properties: dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

class PropertyGraph:
    """In-memory property graph with traversal, search, and persistence."""

    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        # adjacency: node_id -> list of (edge_id, neighbor_id)
        self._adj_out: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self._adj_in: dict[str, list[tuple[str, str]]] = defaultdict(list)
        # index: (label, key, value) -> set of node_ids
        self._node_index: dict[tuple, set[str]] = defaultdict(set)
        self._label_index: dict[str, set[str]] = defaultdict(set)

    # Node operations
    def add_node(self, id: str | None = None, labels: list[str] | None = None,
                 **properties) -> Node:
        if id is None:
            id = str(uuid.uuid4())[:8]
        node = Node(id=id, labels=set(labels or []), properties=properties)
        self._nodes[id] = node
        for label in node.labels:
            self._label_index[label].add(id)
        for k, v in properties.items():
            self._node_index[('', k, json.dumps(v))].add(id)
        return node

    def get_node(self, id: str) -> Optional[Node]:
        return self._nodes.get(id)

    def remove_node(self, id: str) -> None:
        # Remove all edges first
        for eid in list(self._edges):
            e = self._edges[eid]
            if e.source == id or e.target == id:
                self.remove_edge(eid)
        if id in self._nodes:
            node = self._nodes[id]
            for label in node.labels:
                self._label_index[label].discard(id)
            del self._nodes[id]

    def has_node(self, id: str) -> bool:
        return id in self._nodes

    # Edge operations
    def add_edge(self, source: str, target: str, label: str,
                 id: str | None = None, **properties) -> Edge:
        if id is None:
            id = str(uuid.uuid4())[:8]
        edge = Edge(id=id, source=source, target=target,
                    label=label, properties=properties)
        self._edges[id] = edge
        self._adj_out[source].append((id, target))
        self._adj_in[target].append((id, source))
        return edge

    def get_edge(self, id: str) -> Optional[Edge]:
        return self._edges.get(id)

    def remove_edge(self, id: str) -> None:
        if id not in self._edges:
            return
        e = self._edges[id]
        self._adj_out[e.source] = [(i, t) for i, t in self._adj_out[e.source] if i != id]
        self._adj_in[e.target] = [(i, s) for i, s in self._adj_in[e.target] if i != id]
        del self._edges[id]

    # Traversal
    def neighbors(self, node_id: str, edge_label: str | None = None) -> Iterator[Node]:
        for edge_id, neighbor_id in self._adj_out.get(node_id, []):
            if edge_label is None or self._edges[edge_id].label == edge_label:
                yield self._nodes[neighbor_id]

    def predecessors(self, node_id: str, edge_label: str | None = None) -> Iterator[Node]:
        for edge_id, pred_id in self._adj_in.get(node_id, []):
            if edge_label is None or self._edges[edge_id].label == edge_label:
                yield self._nodes[pred_id]

    def bfs(self, start_id: str, edge_label: str | None = None,
            max_depth: int = 3) -> Iterator[tuple[Node, int]]:
        """Breadth-first search yielding (node, depth)."""
        from collections import deque
        visited = {start_id}
        queue = deque([(start_id, 0)])
        while queue:
            nid, depth = queue.popleft()
            yield self._nodes[nid], depth
            if depth >= max_depth:
                continue
            for edge_id, neighbor_id in self._adj_out.get(nid, []):
                if neighbor_id not in visited and (edge_label is None or self._edges[edge_id].label == edge_label):
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

    def dfs(self, start_id: str, edge_label: str | None = None,
            max_depth: int = 3) -> Iterator[Node]:
        """Depth-first search."""
        visited = set()
        def _dfs(nid: str, depth: int):
            if nid in visited or depth > max_depth:
                return
            visited.add(nid)
            yield self._nodes[nid]
            for edge_id, neighbor_id in self._adj_out.get(nid, []):
                if edge_label is None or self._edges[edge_id].label == edge_label:
                    yield from _dfs(neighbor_id, depth + 1)
        yield from _dfs(start_id, 0)

    def shortest_path(self, start_id: str, end_id: str) -> list[str] | None:
        """BFS shortest path. Returns list of node IDs or None."""
        from collections import deque
        if start_id == end_id:
            return [start_id]
        visited = {start_id}
        queue = deque([(start_id, [start_id])])
        while queue:
            nid, path = queue.popleft()
            for edge_id, neighbor_id in self._adj_out.get(nid, []):
                if neighbor_id == end_id:
                    return path + [neighbor_id]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        return None

    # Search
    def find_nodes(self, label: str | None = None, **properties) -> Iterator[Node]:
        for node in self._nodes.values():
            if label and label not in node.labels:
                continue
            if all(node.properties.get(k) == v for k, v in properties.items()):
                yield node

    def find_edges(self, label: str | None = None, **properties) -> Iterator[Edge]:
        for edge in self._edges.values():
            if label and edge.label != label:
                continue
            if all(edge.properties.get(k) == v for k, v in properties.items()):
                yield edge

    # Pattern matching (simple CYPHER-lite)
    def match(self, pattern: str, **kwargs) -> Iterator[dict]:
        """
        Simple pattern matching.
        Pattern: "()-[r:REL]->(n:Label {prop: val})"
        Yields dicts with bound variables.
        """
        import re
        # Very simple: ()-[r:KNOWS]->(n:Person {name: $name})
        arrow_pattern = re.compile(r'\(([a-zA-Z_])\s*(?::(\w+))?\)\s*-\[([a-zA-Z_]):(\w+)\s*(.*?)\]->\(([a-zA-Z_])\s*(?::(\w+))?\)\s*(.*)')
        # Fallback: just yield all edges matching label
        m = re.search(r'\[([a-zA-Z_]?):?(\w+)', pattern)
        if not m:
            return
        edge_label = m.group(2)
        for edge in self.find_edges(label=edge_label):
            src = self.get_node(edge.source)
            tgt = self.get_node(edge.target)
            if src and tgt:
                result = {'_': edge}
                # Try to bind variables based on pattern
                # Very naive — just yield source + target
                yield {'source': src, 'target': tgt, 'edge': edge}

    # Persistence
    def save(self, path: str | Path) -> None:
        data = {
            'name': self.name,
            'nodes': [
                {'id': n.id, 'labels': list(n.labels), 'properties': n.properties}
                for n in self._nodes.values()
            ],
            'edges': [
                {'id': e.id, 'source': e.source, 'target': e.target,
                 'label': e.label, 'properties': e.properties}
                for e in self._edges.values()
            ]
        }
        Path(path).write_text(json.dumps(data, indent=2))

    def load(self, path: str | Path) -> 'PropertyGraph':
        data = json.loads(Path(path).read_text())
        self.name = data['name']
        self._nodes = {n['id']: Node(id=n['id'], labels=set(n['labels']), properties=n['properties'])
                       for n in data['nodes']}
        self._edges = {}
        self._adj_out.clear()
        self._adj_in.clear()
        self._label_index.clear()
        for e in data['edges']:
            self.add_edge(source=e['source'], target=e['target'],
                         label=e['label'], id=e['id'], **e['properties'])
        return self

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"PropertyGraph({self.name!r}, nodes={len(self._nodes)}, edges={len(self._edges)})"
