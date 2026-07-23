# tiny-graph

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](tiny_graph.py)

> Zero-dependency, stdlib-only in-memory property graph for Python.

---

## Why tiny-graph?

| Feature | tiny-graph | NetworkX | igraph | Neo4j |
|---------|-----------|----------|--------|-------|
| **Dependencies** | None (stdlib only) | NumPy, etc. | C extension required | Java server required |
| **Install size** | ~0 KB | ~MB | ~MB | GB |
| **Setup** | `pip install tiny_graph` | `pip install networkx` | compile + install | install + start server |
| **Data store** | In-memory | In-memory | In-memory | External database |
| **Pattern matching** | CYPHER-lite | No | Yes | Full CYPHER |
| **Persistence** | JSON export/load | Pickle only | Pickle only | Built-in |
| **Use case** | Prototyping, embedded graphs, CLI tools | General graph algorithms | Large-scale network analysis | Production graph databases |

---

## Features

- **Node & Edge operations** — add, get, remove, check existence
- **Labels & properties** — flexible labeling and key-value properties on both nodes and edges
- **Graph traversal** — `neighbors()`, `predecessors()`
- **BFS / DFS** — breadth-first and depth-first search with depth limit
- **Shortest path** — BFS-based unweighted shortest path between two nodes
- **Search** — `find_nodes()` and `find_edges()` by label and/or properties
- **Pattern matching** — simple CYPHER-lite pattern syntax `()-[r:REL]->(n:Label)`
- **Persistence** — save/load to/from JSON
- **Zero dependencies** — pure Python stdlib only

---

## Quick Start

### Installation

```bash
pip install tiny-graph
```

Or just copy `tiny_graph.py` into your project — no install needed.

### Social Network Example

```python
from tiny_graph import PropertyGraph

g = PropertyGraph("social")

# Add people
alice = g.add_node(id="alice", labels=["Person"], name="Alice", age=30)
bob   = g.add_node(id="bob",   labels=["Person"], name="Bob",   age=25)
carol = g.add_node(id="carol", labels=["Person"], name="Carol", age=28)
dave  = g.add_node(id="dave",  labels=["Person"], name="Dave",  age=35)

# Add relationships
g.add_edge("alice", "bob",   "KNOWS", since=2020)
g.add_edge("bob",   "carol", "KNOWS", since=2019)
g.add_edge("carol", "dave",  "KNOWS", since=2021)
g.add_edge("alice", "carol", "KNOWS", since=2018)
g.add_edge("dave",  "alice", "KNOWS", since=2017)

print(g)  # PropertyGraph('social', nodes=4, edges=5)
```

---

## Traversal

### Neighbors

```python
# Direct neighbors of Alice
for neighbor in g.neighbors("alice"):
    print(neighbor.properties["name"])

# Carol
```

### BFS — Breadth-First Search

```python
# Explore up to 3 hops from Alice
for node, depth in g.bfs("alice", max_depth=3):
    print(f"{'  ' * depth}{node.properties['name']} (depth={depth})")
```

Output:
```
Alice (depth=0)
  Bob (depth=1)
  Carol (depth=1)
    Dave (depth=2)
```

### DFS — Depth-First Search

```python
# DFS from Alice
for node in g.dfs("alice", max_depth=3):
    print(node.properties["name"])
```

### Shortest Path

```python
# Find shortest path from Alice to Dave
path = g.shortest_path("alice", "dave")
print(path)  # ['alice', 'carol', 'dave']

# Resolve to names
names = [g.get_node(nid).properties["name"] for nid in path]
print(" -> ".join(names))  # Alice -> Carol -> Dave
```

---

## Search

```python
# Find all Person nodes
for node in g.find_nodes(label="Person"):
    print(node.properties["name"])

# Find people by property
for node in g.find_nodes(label="Person", age=28):
    print(node.properties["name"])  # Carol

# Find KNOWS edges
for edge in g.find_edges(label="KNOWS"):
    src = g.get_node(edge.source).properties["name"]
    tgt = g.get_node(edge.target).properties["name"]
    print(f"{src} --[{edge.label}]--> {tgt}")
```

---

## Pattern Matching (CYPHER-lite)

```python
# Simple CYPHER-lite pattern: ()-[r:KNOWS]->(n:Person)
for result in g.match("()-[r:KNOWS]->(n:Person)"):
    print(result["source"].properties["name"],
          "-[KNOWS]->",
          result["target"].properties["name"])
```

---

## Persistence

```python
from tiny_graph import PropertyGraph

g = PropertyGraph("social")

# ... build your graph ...

# Save to JSON
g.save("social_graph.json")

# Load from JSON
g2 = PropertyGraph()
g2.load("social_graph.json")
print(g2)  # PropertyGraph('social', nodes=4, edges=5)
```

The saved JSON schema:

```json
{
  "name": "social",
  "nodes": [
    {
      "id": "alice",
      "labels": ["Person"],
      "properties": { "name": "Alice", "age": 30 }
    }
  ],
  "edges": [
    {
      "id": "abc123",
      "source": "alice",
      "target": "bob",
      "label": "KNOWS",
      "properties": { "since": 2020 }
    }
  ]
}
```

---

## License

MIT License. See [LICENSE](LICENSE).
