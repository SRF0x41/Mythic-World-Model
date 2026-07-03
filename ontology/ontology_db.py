import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "ontology.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    The ontology database is the central graph store. It mirrors the concept
    network from the concepts layer and provides traversal, pathfinding,
    and reasoning queries across the full knowledge graph.

    In addition to concepts and relations, it stores cross-layer provenance
    links so any concept can be traced back through signals, evidence, and
    sources, and forward through hypotheses, models, and world models.
    """
    conn = get_connection()
    conn.executescript("""
        -- Core concept nodes in the ontology graph
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            node_type TEXT NOT NULL DEFAULT 'concept'
                CHECK(node_type IN ('concept', 'signal', 'hypothesis', 'model', 'world_model')),
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Directed edges: influences, opposes, related_to, contributes_to, parent_of, child_of
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES nodes(id),
            target_id TEXT NOT NULL REFERENCES nodes(id),
            edge_type TEXT NOT NULL,
            strength REAL CHECK(strength BETWEEN 0.0 AND 1.0),
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source_id, target_id, edge_type)
        );

        -- Cross-layer provenance: which evidence/signals support which concepts
        CREATE TABLE IF NOT EXISTS provenance (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL REFERENCES nodes(id),
            supports_id TEXT NOT NULL,
            supports_type TEXT NOT NULL
                CHECK(supports_type IN ('evidence', 'signal', 'source', 'hypothesis', 'model', 'world_model')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(node_id, supports_id, supports_type)
        );

        -- Observations: notes, annotations, or AI-generated insights about nodes/edges
        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL REFERENCES nodes(id),
            observation_type TEXT NOT NULL
                CHECK(observation_type IN ('note', 'insight', 'definition_update', 'correction')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Indexes for fast graph traversal
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);
        CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
        CREATE INDEX IF NOT EXISTS idx_provenance_node ON provenance(node_id);
        CREATE INDEX IF NOT EXISTS idx_provenance_supports ON provenance(supports_id);
        CREATE INDEX IF NOT EXISTS idx_observations_target ON observations(target_id);
    """)
    conn.commit()
    conn.close()


def add_node(name, *, node_type="concept", description=None, confidence_score=None):
    """Add a node to the ontology graph. Returns node id."""
    conn = get_connection()
    node_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO nodes (id, name, description, node_type, confidence_score, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (node_id, name, description, node_type, confidence_score, now, now),
    )
    conn.commit()
    conn.close()
    return node_id


def add_edge(source_id, target_id, edge_type, *, strength=None, description=None):
    """Add a directed edge between two nodes. Returns edge id."""
    conn = get_connection()
    edge_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """INSERT INTO edges (id, source_id, target_id, edge_type, strength, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (edge_id, source_id, target_id, edge_type, strength, description, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Edge already exists — return existing
        existing = conn.execute(
            "SELECT id FROM edges WHERE source_id=? AND target_id=? AND edge_type=?",
            (source_id, target_id, edge_type),
        ).fetchone()
        conn.close()
        return existing["id"] if existing else None
    conn.close()
    return edge_id


def add_provenance(node_id, supports_id, supports_type):
    """Link a node to a supporting object from another layer."""
    conn = get_connection()
    prov_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO provenance (id, node_id, supports_id, supports_type) VALUES (?, ?, ?, ?)",
            (prov_id, node_id, supports_id, supports_type),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return prov_id


def add_observation(target_id, observation_type, content):
    """Add an observation (note, insight, correction) about a node."""
    conn = get_connection()
    obs_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO observations (id, target_id, observation_type, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (obs_id, target_id, observation_type, content, now),
    )
    conn.commit()
    conn.close()
    return obs_id


def get_node(node_id):
    """Return a single node dict or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_node_by_name(name):
    """Look up a node by name."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM nodes WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_neighbors(node_id, *, direction="outgoing", edge_type=None):
    """
    Get directly connected neighbors.
    direction: 'outgoing' (node → neighbor), 'incoming' (neighbor → node), or 'both'.
    """
    conn = get_connection()
    neighbors = []

    if direction in ("outgoing", "both"):
        query = """SELECT n.*, e.edge_type, e.strength, e.description
                   FROM edges e JOIN nodes n ON n.id = e.target_id
                   WHERE e.source_id = ?"""
        params = [node_id]
        if edge_type:
            query += " AND e.edge_type = ?"
            params.append(edge_type)
        neighbors.extend([dict(r) for r in conn.execute(query, params).fetchall()])

    if direction in ("incoming", "both"):
        query = """SELECT n.*, e.edge_type, e.strength, e.description
                   FROM edges e JOIN nodes n ON n.id = e.source_id
                   WHERE e.target_id = ?"""
        params = [node_id]
        if edge_type:
            query += " AND e.edge_type = ?"
            params.append(edge_type)
        neighbors.extend([dict(r) for r in conn.execute(query, params).fetchall()])

    conn.close()
    return neighbors


def find_paths(start_id, end_id, *, max_depth=5, edge_type=None):
    """
    Find all paths between two nodes up to max_depth using BFS.
    Returns list of paths, where each path is a list of node dicts with edge info.
    """
    conn = get_connection()

    def bfs():
        # Queue: (current_node_id, path_so_far)
        queue = [(start_id, [get_node_row(start_id)])]
        visited = {start_id}
        results = []

        while queue and len(queue[0][1]) <= max_depth:
            current, path = queue.pop(0)

            if current == end_id and len(path) > 1:
                results.append(path)
                continue

            if len(path) > max_depth:
                continue

            # Get outgoing edges
            edge_query = "SELECT * FROM edges WHERE source_id = ?"
            edge_params = [current]
            if edge_type:
                edge_query += " AND edge_type = ?"
                edge_params.append(edge_type)

            for edge in conn.execute(edge_query, edge_params).fetchall():
                next_id = edge["target_id"]
                if next_id not in visited:
                    visited.add(next_id)
                    next_node = conn.execute(
                        "SELECT * FROM nodes WHERE id = ?", (next_id,)
                    ).fetchone()
                    if next_node:
                        new_path = path + [dict(next_node)]
                        new_path[-2]["_edge_to_next"] = dict(edge)
                        queue.append((next_id, new_path))

        return results

    def get_node_row(node_id):
        row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return dict(row) if row else None

    paths = bfs()
    conn.close()
    return paths


def get_subgraph(node_id, *, depth=2, edge_types=None):
    """
    Get the subgraph centered on a node, expanding out to given depth.
    Returns dict with 'nodes' and 'edges' lists.
    """
    conn = get_connection()
    seen_nodes = {node_id}
    seen_edges = set()
    node_list = []
    edge_list = []

    # BFS expansion
    frontier = [node_id]
    for _ in range(depth):
        next_frontier = []
        for nid in frontier:
            # Get all edges from this node
            edge_query = "SELECT * FROM edges WHERE source_id = ? OR target_id = ?"
            if edge_types:
                placeholders = ", ".join("?" for _ in edge_types)
                edge_query += f" AND edge_type IN ({placeholders})"
                params = [nid, nid] + list(edge_types)
            else:
                params = [nid, nid]

            for edge in conn.execute(edge_query, params).fetchall():
                edge_key = (edge["source_id"], edge["target_id"], edge["edge_type"])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edge_list.append(dict(edge))

                    for eid in (edge["source_id"], edge["target_id"]):
                        if eid not in seen_nodes:
                            seen_nodes.add(eid)
                            row = conn.execute(
                                "SELECT * FROM nodes WHERE id = ?", (eid,)
                            ).fetchone()
                            if row:
                                node_list.append(dict(row))
                                next_frontier.append(eid)

        frontier = next_frontier

    # Include the center node
    center = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if center:
        node_list.insert(0, dict(center))

    conn.close()
    return {"nodes": node_list, "edges": edge_list}


def list_nodes(*, node_type=None, limit=100, offset=0):
    """List nodes, optionally filtered by type."""
    conn = get_connection()
    query = "SELECT * FROM nodes WHERE 1=1"
    params = []
    if node_type:
        query += " AND node_type = ?"
        params.append(node_type)
    query += " ORDER BY name LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_nodes(query_text):
    """Search nodes by name or description."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM nodes WHERE name LIKE ? OR description LIKE ? ORDER BY name LIMIT 100",
        (pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_provenance_chain(node_id):
    """Trace provenance from a node back through all linked supporting objects."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM provenance WHERE node_id = ? ORDER BY supports_type",
        (node_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_observations(node_id):
    """Get all observations about a node."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM observations WHERE target_id = ? ORDER BY created_at DESC",
        (node_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_statistics():
    """Get overview statistics about the ontology graph."""
    conn = get_connection()
    stats = {}
    stats["total_nodes"] = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    stats["total_edges"] = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    stats["total_provenance"] = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    stats["total_observations"] = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

    # Node type breakdown
    stats["by_type"] = {
        r["node_type"]: r["count"]
        for r in conn.execute(
            "SELECT node_type, COUNT(*) as count FROM nodes GROUP BY node_type"
        ).fetchall()
    }

    # Edge type breakdown
    stats["edge_types"] = {
        r["edge_type"]: r["count"]
        for r in conn.execute(
            "SELECT edge_type, COUNT(*) as count FROM edges GROUP BY edge_type"
        ).fetchall()
    }

    conn.close()
    return stats
