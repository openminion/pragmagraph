"""Internal SQLite row-update and traversal operations."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from typing import Any

from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OmittedDiagnostic,
    PathResult,
    QueryHit,
    QueryResult,
    SourceRef,
)


def table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ?", (name,)
        ).fetchone()
        is not None
    )


def node_search_text(node: GraphNode) -> str:
    return " ".join(
        (
            node.id,
            node.kind,
            node.label,
            node.source_ref.path,
            node.source_ref.section,
            node.text,
            " ".join(str(value) for value in node.metadata.values()),
        )
    )


def node_from_payload(payload: object) -> GraphNode:
    return GraphNode.from_dict(json.loads(str(payload)))


def edge_from_payload(payload: object) -> GraphEdge:
    return GraphEdge.from_dict(json.loads(str(payload)))


def node_by_id(connection: sqlite3.Connection, node_id: str) -> GraphNode | None:
    row = connection.execute(
        "SELECT payload FROM nodes WHERE id = ?", (node_id,)
    ).fetchone()
    return node_from_payload(row["payload"]) if row is not None else None


def incident_edges(
    connection: sqlite3.Connection,
    node_id: str,
    *,
    edge_kinds: tuple[str, ...] = (),
) -> tuple[GraphEdge, ...]:
    params: list[str] = [node_id, node_id]
    kind_clause = ""
    if edge_kinds:
        kind_clause = f" AND kind IN ({','.join('?' for _ in edge_kinds)})"
        params.extend(edge_kinds)
    rows = connection.execute(
        f"""
        SELECT payload FROM edges
        WHERE (source_id = ? OR target_id = ?){kind_clause}
        ORDER BY id
        """,
        tuple(params),
    ).fetchall()
    return tuple(edge_from_payload(row["payload"]) for row in rows)


def apply_node_delta(
    connection: sqlite3.Connection,
    removed_ids: list[str],
    changed_nodes: list[GraphNode],
) -> None:
    for node_id in removed_ids:
        connection.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        connection.execute(
            "DELETE FROM source_refs WHERE owner_type = 'node' AND owner_id = ?",
            (node_id,),
        )
        if table_exists(connection, "node_fts"):
            connection.execute("DELETE FROM node_fts WHERE id = ?", (node_id,))
        if table_exists(connection, "node_fts_trigram"):
            connection.execute("DELETE FROM node_fts_trigram WHERE id = ?", (node_id,))
    for node in changed_nodes:
        connection.execute(
            """
            INSERT OR REPLACE INTO nodes
            (id, kind, label, source_path, text, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                node.id,
                node.kind,
                node.label,
                node.source_ref.path,
                node.text,
                json.dumps(node.to_dict(), sort_keys=True),
            ),
        )
        connection.execute(
            "DELETE FROM source_refs WHERE owner_type = 'node' AND owner_id = ?",
            (node.id,),
        )
        connection.execute(
            """
            INSERT INTO source_refs
            (owner_type, owner_id, path, line, column, section, uri)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            source_ref_row("node", node.id, node.source_ref),
        )
        if table_exists(connection, "node_fts"):
            connection.execute("DELETE FROM node_fts WHERE id = ?", (node.id,))
            connection.execute(
                """
                INSERT INTO node_fts (id, kind, label, source_path, text, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.kind,
                    node.label,
                    node.source_ref.path,
                    node.text,
                    " ".join(str(value) for value in node.metadata.values()),
                ),
            )
        if table_exists(connection, "node_fts_trigram"):
            connection.execute("DELETE FROM node_fts_trigram WHERE id = ?", (node.id,))
            connection.execute(
                "INSERT INTO node_fts_trigram (id, searchable) VALUES (?, ?)",
                (node.id, node_search_text(node)),
            )


def apply_edge_delta(
    connection: sqlite3.Connection,
    removed_ids: list[str],
    changed_edges: list[GraphEdge],
) -> None:
    for edge_id in removed_ids:
        connection.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
        connection.execute(
            "DELETE FROM source_refs WHERE owner_type = 'edge' AND owner_id = ?",
            (edge_id,),
        )
    for edge in changed_edges:
        connection.execute(
            """
            INSERT OR REPLACE INTO edges
            (id, kind, source_id, target_id, source_path, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                edge.id,
                edge.kind,
                edge.source_id,
                edge.target_id,
                edge.source_ref.path,
                json.dumps(edge.to_dict(), sort_keys=True),
            ),
        )
        connection.execute(
            "DELETE FROM source_refs WHERE owner_type = 'edge' AND owner_id = ?",
            (edge.id,),
        )
        connection.execute(
            """
            INSERT INTO source_refs
            (owner_type, owner_id, path, line, column, section, uri)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            source_ref_row("edge", edge.id, edge.source_ref),
        )


def replace_omitted(connection: sqlite3.Connection, snapshot: GraphSnapshot) -> None:
    connection.execute("DELETE FROM omitted")
    for item in sorted(
        snapshot.omitted, key=lambda value: (value.reason, value.item_id)
    ):
        connection.execute(
            "INSERT INTO omitted (reason, item_id, payload) VALUES (?, ?, ?)",
            (item.reason, item.item_id, json.dumps(item.to_dict(), sort_keys=True)),
        )


def fail_if_requested(actual: str, expected: str) -> None:
    if actual == expected:
        raise sqlite3.OperationalError(f"injected failure after {expected}")


def sqlite_neighborhood(
    connection: sqlite3.Connection,
    node_id: str,
    *,
    depth: int,
    max_results: int,
    edge_kinds: tuple[str, ...],
    node_kinds: tuple[str, ...],
) -> QueryResult:
    visited = {node_id}
    queue: deque[tuple[str, int]] = deque([(node_id, 0)])
    found: list[GraphNode] = []
    rows_examined = 0
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        edges = incident_edges(connection, current, edge_kinds=edge_kinds)
        rows_examined += len(edges)
        for edge in edges:
            other = edge.target_id if edge.source_id == current else edge.source_id
            if other in visited:
                continue
            visited.add(other)
            node = node_by_id(connection, other)
            if node is None or (node_kinds and node.kind not in node_kinds):
                continue
            found.append(node)
            queue.append((other, current_depth + 1))
    hits = tuple(
        QueryHit(
            node=node,
            score=max(1.0, float(max_results - index)),
            edges=incident_edges(connection, node.id),
            snippet=node.text or node.label or node.source_ref.path or node.id,
        )
        for index, node in enumerate(found[:max_results])
    )
    omitted = ()
    if len(found) > max_results:
        omitted = (
            OmittedDiagnostic(
                reason="max_results",
                item_id=node_id,
                details={"omitted": len(found) - max_results},
            ),
        )
    return QueryResult(
        query=node_id,
        hits=hits,
        omitted=omitted,
        diagnostics={
            "depth": depth,
            "candidate_count": len(found),
            "strategy": "indexed_traversal",
            "rows_examined": rows_examined,
            "snapshot_deserialized": False,
        },
    )


def sqlite_path(
    connection: sqlite3.Connection,
    source_id: str,
    target_id: str,
    *,
    max_hops: int,
    edge_kinds: tuple[str, ...],
    node_kinds: tuple[str, ...],
) -> PathResult:
    queue: deque[tuple[str, list[GraphEdge]]] = deque([(source_id, [])])
    visited = {source_id}
    rows_examined = 0
    while queue:
        current, edge_path = queue.popleft()
        if current == target_id:
            ids = [source_id]
            cursor = source_id
            for edge in edge_path:
                cursor = edge.target_id if edge.source_id == cursor else edge.source_id
                ids.append(cursor)
            nodes = tuple(
                node
                for item in ids
                for node in (node_by_id(connection, item),)
                if node is not None
            )
            if node_kinds and any(node.kind not in node_kinds for node in nodes):
                continue
            return PathResult(
                source_id=source_id,
                target_id=target_id,
                nodes=nodes,
                edges=tuple(edge_path),
                diagnostics={
                    "strategy": "indexed_traversal",
                    "rows_examined": rows_examined,
                    "snapshot_deserialized": False,
                },
            )
        if len(edge_path) >= max_hops:
            continue
        edges = incident_edges(connection, current, edge_kinds=edge_kinds)
        rows_examined += len(edges)
        for edge in edges:
            next_id = edge.target_id if edge.source_id == current else edge.source_id
            if next_id in visited:
                continue
            visited.add(next_id)
            queue.append((next_id, [*edge_path, edge]))
    return PathResult(
        source_id=source_id,
        target_id=target_id,
        omitted=(
            OmittedDiagnostic(
                reason="path_not_found",
                item_id=target_id,
                details={"max_hops": max_hops},
            ),
        ),
        diagnostics={
            "strategy": "indexed_traversal",
            "rows_examined": rows_examined,
            "snapshot_deserialized": False,
        },
    )


def source_ref_row(
    owner_type: str, owner_id: str, source_ref: SourceRef
) -> tuple[Any, ...]:
    return (
        owner_type,
        owner_id,
        source_ref.path,
        source_ref.line,
        source_ref.column,
        source_ref.section,
        source_ref.uri,
    )


__all__ = [
    "apply_edge_delta",
    "apply_node_delta",
    "edge_from_payload",
    "fail_if_requested",
    "incident_edges",
    "node_by_id",
    "node_from_payload",
    "node_search_text",
    "replace_omitted",
    "sqlite_neighborhood",
    "sqlite_path",
    "source_ref_row",
    "table_exists",
]
