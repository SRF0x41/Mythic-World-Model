# Ontology — The Knowledge Graph

The ontology is the **central graph store** for the entire system. It mirrors the concept network and provides traversal, pathfinding, and reasoning queries across all layers.

### Purpose

While the `concepts/` layer stores individual concept objects, the ontology layer treats the full network as a queryable graph. It supports:

- Graph traversal (neighbors, subgraphs, paths between nodes)
- Cross-layer provenance tracing (concept → signal → evidence → source)
- Observations and annotations on any node
- Statistics and health checks on the knowledge graph

### Question Answered

> What connects to what, and how can I navigate the full network?

### Schema

**`nodes`** — graph nodes of any type (concept, signal, hypothesis, model, world_model). Each has `id`, `name`, `description`, `node_type`, `confidence_score`.

**`edges`** — directed relationships between nodes (influences, opposes, related_to, contributes_to, parent_of, child_of). Each has `source_id`, `target_id`, `edge_type`, `strength`.

**`provenance`** — cross-layer links connecting ontology nodes to supporting objects from other layers (evidence, signals, sources).

**`observations`** — notes, insights, definition updates, or corrections attached to any node.

### API

- `init_db()` — create tables
- `add_node(name, node_type, ...)` — add a node to the graph
- `add_edge(source, target, type, ...)` — add a directed edge
- `add_provenance(node_id, supports_id, supports_type)` — link cross-layer provenance
- `add_observation(target_id, type, content)` — annotate a node
- `get_node(id)` / `get_node_by_name(name)` — look up a node
- `get_neighbors(id, direction, edge_type)` — get directly connected nodes
- `find_paths(start, end, max_depth)` — BFS pathfinding between two nodes
- `get_subgraph(id, depth, edge_types)` — extract the local neighborhood
- `list_nodes(node_type)` / `search_nodes(query)` — browse and search
- `get_provenance_chain(id)` — trace full provenance for a node
- `get_observations(id)` — get annotations on a node
- `get_statistics()` — overview stats for the entire graph
