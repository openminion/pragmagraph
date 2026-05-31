"""Deterministic query helpers over PragmaGraph snapshots."""

from __future__ import annotations

import re
from collections import deque

from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    HealthSummary,
    OmittedDiagnostic,
    PathResult,
    QueryHit,
    QueryRequest,
    QueryResult,
)


def _tokens(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-zA-Z0-9_]+", text.lower()) if token}


def _node_text(node: GraphNode) -> str:
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


def _incident_edges(snapshot: GraphSnapshot, node_id: str) -> tuple[GraphEdge, ...]:
    return tuple(
        edge
        for edge in snapshot.edges
        if edge.source_id == node_id or edge.target_id == node_id
    )


def _score_node(node: GraphNode, request: QueryRequest) -> float:
    if node.id in request.node_ids:
        return 1000.0
    query = request.query.strip().lower()
    if not query:
        return 0.0
    haystack = _node_text(node).lower()
    score = 0.0
    if query == node.id.lower():
        score += 900.0
    if query == node.source_ref.path.lower():
        score += 700.0
    if query == node.label.lower():
        score += 500.0
    if query in haystack:
        score += 50.0
    query_tokens = _tokens(query)
    if query_tokens:
        overlap = query_tokens & _tokens(haystack)
        score += len(overlap) * 10.0
    return score


def _snippet(node: GraphNode) -> str:
    return node.text or node.label or node.source_ref.path or node.id


def query(snapshot: GraphSnapshot, request: QueryRequest | str) -> QueryResult:
    """Run deterministic lexical/structural search over a snapshot."""
    req = request if isinstance(request, QueryRequest) else QueryRequest(query=request)
    scored = [
        (_score_node(node, req), node)
        for node in snapshot.nodes
        if _score_node(node, req) > 0
    ]
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].kind,
            item[1].source_ref.path,
            item[1].id,
        )
    )
    hits = tuple(
        QueryHit(
            node=node,
            score=score,
            edges=_incident_edges(snapshot, node.id) if req.include_edges else (),
            snippet=_snippet(node),
        )
        for score, node in scored[: req.max_results]
    )
    omitted = ()
    if len(scored) > req.max_results:
        omitted = (
            OmittedDiagnostic(
                reason="max_results",
                item_id="query",
                details={"omitted": len(scored) - req.max_results},
            ),
        )
    return QueryResult(
        query=req.query,
        hits=hits,
        omitted=omitted,
        diagnostics={"candidate_count": len(scored)},
    )


def neighborhood(
    snapshot: GraphSnapshot,
    node_id: str,
    *,
    depth: int = 1,
    max_results: int = 10,
) -> QueryResult:
    """Return cited nodes around ``node_id``."""
    node_map = snapshot.node_map()
    visited = {node_id}
    queue: deque[tuple[str, int]] = deque([(node_id, 0)])
    found: list[GraphNode] = []
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for edge in _incident_edges(snapshot, current):
            other = edge.target_id if edge.source_id == current else edge.source_id
            if other in visited:
                continue
            visited.add(other)
            node = node_map.get(other)
            if node is None:
                continue
            found.append(node)
            queue.append((other, current_depth + 1))
    hits = tuple(
        QueryHit(
            node=node,
            score=max(1.0, float(max_results - index)),
            edges=_incident_edges(snapshot, node.id),
            snippet=_snippet(node),
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
        diagnostics={"depth": depth, "candidate_count": len(found)},
    )


def path(
    snapshot: GraphSnapshot,
    source_id: str,
    target_id: str,
    *,
    max_hops: int = 4,
) -> PathResult:
    """Find one deterministic bounded path between two nodes."""
    node_map = snapshot.node_map()
    adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        adjacency.setdefault(edge.source_id, []).append((edge.target_id, edge))
        adjacency.setdefault(edge.target_id, []).append((edge.source_id, edge))
    queue: deque[tuple[str, list[GraphEdge]]] = deque([(source_id, [])])
    visited = {source_id}
    while queue:
        current, edge_path = queue.popleft()
        if current == target_id:
            ids = [source_id]
            cursor = source_id
            for edge in edge_path:
                cursor = edge.target_id if edge.source_id == cursor else edge.source_id
                ids.append(cursor)
            return PathResult(
                source_id=source_id,
                target_id=target_id,
                nodes=tuple(node_map[node] for node in ids if node in node_map),
                edges=tuple(edge_path),
            )
        if len(edge_path) >= max_hops:
            continue
        for next_id, edge in adjacency.get(current, ()):
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
    )


def health(snapshot: GraphSnapshot) -> HealthSummary:
    """Return a deterministic snapshot health summary."""
    return HealthSummary(
        ok=snapshot.schema_version != "",
        schema_version=snapshot.schema_version,
        namespace=snapshot.namespace,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        omitted_count=len(snapshot.omitted),
        stats=dict(snapshot.stats),
    )


__all__ = [
    "health",
    "neighborhood",
    "path",
    "query",
]
