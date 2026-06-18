"""Deterministic query helpers over PragmaGraph snapshots."""

from __future__ import annotations

import re
from collections import deque

from pragmagraph.contracts import (
    EDGE_GIT_CHANGES_PATH,
    EDGE_GIT_TOUCHES,
    NODE_FILE,
    NODE_GIT_CHANGED_PATH,
    NODE_GIT_COMMIT,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    HealthSummary,
    OmittedDiagnostic,
    PathResult,
    QueryExplanation,
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


def _matches_edge_filters(
    edge: GraphEdge,
    *,
    edge_kinds: tuple[str, ...] = (),
) -> bool:
    return not edge_kinds or edge.kind in edge_kinds


def _matches_node_filters(
    node: GraphNode,
    *,
    node_kinds: tuple[str, ...] = (),
) -> bool:
    return not node_kinds or node.kind in node_kinds


def _score_node(
    node: GraphNode, request: QueryRequest
) -> tuple[float, QueryExplanation]:
    score_parts: dict[str, float] = {}
    matched_fields: list[str] = []
    exact_match = ""
    if node.id in request.node_ids:
        score_parts["requested_node_id"] = 1000.0
        matched_fields.append("id")
        exact_match = "id"
    query = request.query.strip().lower()
    if not query:
        return sum(score_parts.values()), QueryExplanation(
            matched_fields=tuple(matched_fields),
            exact_match=exact_match,
            score_parts=score_parts,
            omitted_reasons=("empty_query",),
        )
    haystack = _node_text(node).lower()
    if query == node.id.lower():
        score_parts["exact_id"] = 900.0
        matched_fields.append("id")
        exact_match = "id"
    if query == node.source_ref.path.lower():
        score_parts["exact_path"] = 700.0
        matched_fields.append("source_ref.path")
        exact_match = "source_ref.path"
    if query == node.label.lower():
        score_parts["exact_label"] = 500.0
        matched_fields.append("label")
        exact_match = "label"
    if query in haystack:
        score_parts["substring"] = 50.0
        matched_fields.append("haystack")
    query_tokens = _tokens(query)
    matched_tokens: tuple[str, ...] = ()
    if query_tokens:
        overlap = query_tokens & _tokens(haystack)
        matched_tokens = tuple(sorted(overlap))
        if overlap:
            score_parts["token_overlap"] = len(overlap) * 10.0
            matched_fields.append("tokens")
    return sum(score_parts.values()), QueryExplanation(
        matched_fields=tuple(dict.fromkeys(matched_fields)),
        matched_tokens=matched_tokens,
        exact_match=exact_match,
        score_parts=score_parts,
    )


def _snippet(node: GraphNode) -> str:
    return node.text or node.label or node.source_ref.path or node.id


def query(snapshot: GraphSnapshot, request: QueryRequest | str) -> QueryResult:
    """Run deterministic lexical/structural search over a snapshot."""
    req = request if isinstance(request, QueryRequest) else QueryRequest(query=request)
    scored = [
        (score, explanation, node)
        for node in snapshot.nodes
        for score, explanation in (_score_node(node, req),)
        if score > 0
    ]
    scored.sort(
        key=lambda item: (
            -item[0],
            item[2].kind,
            item[2].source_ref.path,
            item[2].id,
        )
    )
    hits = tuple(
        QueryHit(
            node=node,
            score=score,
            edges=_incident_edges(snapshot, node.id) if req.include_edges else (),
            snippet=_snippet(node),
            explanation=explanation,
        )
        for score, explanation, node in scored[: req.max_results]
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
    edge_kinds: tuple[str, ...] = (),
    node_kinds: tuple[str, ...] = (),
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
            if not _matches_edge_filters(edge, edge_kinds=edge_kinds):
                continue
            other = edge.target_id if edge.source_id == current else edge.source_id
            if other in visited:
                continue
            visited.add(other)
            node = node_map.get(other)
            if node is None:
                continue
            if not _matches_node_filters(node, node_kinds=node_kinds):
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
    edge_kinds: tuple[str, ...] = (),
    node_kinds: tuple[str, ...] = (),
) -> PathResult:
    """Find one deterministic bounded path between two nodes."""
    node_map = snapshot.node_map()
    adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if not _matches_edge_filters(edge, edge_kinds=edge_kinds):
            continue
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
            nodes = tuple(node_map[node] for node in ids if node in node_map)
            if node_kinds and any(node.kind not in node_kinds for node in nodes):
                continue
            return PathResult(
                source_id=source_id,
                target_id=target_id,
                nodes=nodes,
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


def reverse_dependencies(
    snapshot: GraphSnapshot,
    target_id: str,
    *,
    max_results: int = 10,
) -> QueryResult:
    """Return config nodes that depend on ``target_id``."""
    node_map = snapshot.node_map()
    hits = []
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if edge.kind != "depends_on" or edge.target_id != target_id:
            continue
        node = node_map.get(edge.source_id)
        if node is None:
            continue
        hits.append(
            QueryHit(
                node=node,
                score=100.0,
                edges=(edge,),
                snippet=_snippet(node),
                explanation=QueryExplanation(
                    matched_fields=("edge.depends_on",),
                    score_parts={"reverse_dependency": 100.0},
                ),
            )
        )
    return QueryResult(
        query=target_id,
        hits=tuple(hits[:max_results]),
        omitted=_max_results_omitted(target_id, len(hits), max_results),
        diagnostics={"resolution_kind": "static_reverse_dependency"},
    )


def reverse_imports(
    snapshot: GraphSnapshot,
    target_id: str,
    *,
    max_results: int = 10,
) -> QueryResult:
    """Return importer files for one resolved module target."""
    node_map = snapshot.node_map()
    importer_ids: list[str] = []
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if (
            edge.kind == "imports"
            and edge.target_id == target_id
            and edge.metadata.get("resolved") is True
        ):
            import_node = node_map.get(edge.source_id)
            if import_node is None:
                continue
            source_path = str(import_node.metadata.get("source_path", "") or "")
            for candidate_edge in _incident_edges(snapshot, import_node.id):
                if (
                    candidate_edge.kind == "imports"
                    and candidate_edge.source_id != import_node.id
                ):
                    importer_ids.append(candidate_edge.source_id)
            if source_path:
                for node in snapshot.nodes:
                    if node.kind == "file" and node.source_ref.path == source_path:
                        importer_ids.append(node.id)
    hits = []
    seen: set[str] = set()
    for importer_id in importer_ids:
        if importer_id in seen:
            continue
        seen.add(importer_id)
        node = node_map.get(importer_id)
        if node is None:
            continue
        hits.append(
            QueryHit(
                node=node,
                score=100.0,
                edges=_incident_edges(snapshot, node.id),
                snippet=_snippet(node),
                explanation=QueryExplanation(
                    matched_fields=("edge.imports",),
                    score_parts={"resolved_reverse_import": 100.0},
                ),
            )
        )
    return QueryResult(
        query=target_id,
        hits=tuple(hits[:max_results]),
        omitted=_max_results_omitted(target_id, len(hits), max_results),
        diagnostics={"resolution_kind": "static_resolved_import"},
    )


def backlinks(
    snapshot: GraphSnapshot,
    target_id: str,
    *,
    max_results: int = 10,
) -> QueryResult:
    """Return document/file nodes that link to ``target_id``."""
    node_map = snapshot.node_map()
    hits = []
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if edge.kind not in {"references_doc", "references_section"}:
            continue
        if edge.target_id != target_id:
            continue
        node = node_map.get(edge.source_id)
        if node is None:
            continue
        hits.append(
            QueryHit(
                node=node,
                score=100.0,
                edges=(edge,),
                snippet=_snippet(node),
                explanation=QueryExplanation(
                    matched_fields=("edge.backlink",),
                    score_parts={"backlink": 100.0},
                ),
            )
        )
    return QueryResult(
        query=target_id,
        hits=tuple(hits[:max_results]),
        omitted=_max_results_omitted(target_id, len(hits), max_results),
        diagnostics={"resolution_kind": "static_backlink"},
    )


def impact(
    snapshot: GraphSnapshot,
    node_id: str,
    *,
    max_results: int = 10,
) -> QueryResult:
    """Return high-confidence inbound impact for one node."""
    node_map = snapshot.node_map()
    hits: list[QueryHit] = []
    omitted: list[OmittedDiagnostic] = []
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if edge.target_id != node_id:
            continue
        resolution_kind = _edge_resolution_kind(edge, node_map)
        if resolution_kind in {"heuristic", "unsupported"}:
            omitted.append(
                OmittedDiagnostic(
                    reason="impact_edge_unresolved",
                    item_id=edge.id,
                    details={
                        "edge_kind": edge.kind,
                        "resolution_kind": resolution_kind,
                    },
                )
            )
            continue
        node = node_map.get(edge.source_id)
        if node is None:
            continue
        hits.append(
            QueryHit(
                node=node,
                score=100.0,
                edges=(edge,),
                snippet=_snippet(node),
                explanation=QueryExplanation(
                    matched_fields=(f"edge.{edge.kind}",),
                    score_parts={"impact": 100.0},
                    exact_match=resolution_kind,
                ),
            )
        )
    if len(hits) > max_results:
        omitted.extend(_max_results_omitted(node_id, len(hits), max_results))
    return QueryResult(
        query=node_id,
        hits=tuple(hits[:max_results]),
        omitted=tuple(omitted),
        diagnostics={"resolution_kind": "high_confidence_static_only"},
    )


def recent_commits_for_path(
    snapshot: GraphSnapshot,
    target_path: str,
    *,
    max_results: int = 10,
) -> QueryResult:
    """Return recent git commit nodes affecting one relative path."""
    normalized_path = target_path.strip().strip("/")
    node_map = snapshot.node_map()
    commit_ids: set[str] = set()
    commit_edges: dict[str, list[GraphEdge]] = {}
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if edge.kind not in {EDGE_GIT_TOUCHES, EDGE_GIT_CHANGES_PATH}:
            continue
        target = node_map.get(edge.target_id)
        if target is None:
            continue
        edge_path = target.source_ref.path or target.label
        if edge_path != normalized_path:
            continue
        source = node_map.get(edge.source_id)
        if source is None or source.kind != NODE_GIT_COMMIT:
            continue
        commit_ids.add(source.id)
        commit_edges.setdefault(source.id, []).append(edge)
    commits = sorted(
        (node_map[commit_id] for commit_id in commit_ids if commit_id in node_map),
        key=_git_commit_sort_key,
    )
    hits = tuple(
        QueryHit(
            node=node,
            score=float(max(max_results - index, 1)),
            edges=tuple(
                sorted(commit_edges.get(node.id, ()), key=lambda item: item.id)
            ),
            snippet=node.text or node.label,
            explanation=QueryExplanation(
                matched_fields=("edge.git_path",),
                score_parts={"git_path_commit": 100.0},
                exact_match="path",
            ),
        )
        for index, node in enumerate(commits[:max_results])
    )
    return QueryResult(
        query=normalized_path,
        hits=hits,
        omitted=_max_results_omitted(normalized_path, len(commits), max_results),
        diagnostics={
            "resolution_kind": "static_git_overlay",
            "target_path": normalized_path,
        },
    )


def files_touched_by_commit(
    snapshot: GraphSnapshot,
    commit_ref: str,
    *,
    max_results: int = 50,
) -> QueryResult:
    """Return file/path nodes touched by one git commit."""
    commit_node = _resolve_commit_node(snapshot, commit_ref)
    if commit_node is None:
        return QueryResult(
            query=commit_ref,
            omitted=(
                OmittedDiagnostic(
                    reason="git_commit_not_found",
                    item_id=commit_ref,
                ),
            ),
            diagnostics={"resolution_kind": "missing_git_commit"},
        )
    node_map = snapshot.node_map()
    hits: list[QueryHit] = []
    candidate_edges = sorted(
        (
            edge
            for edge in snapshot.edges
            if edge.source_id == commit_node.id
            and edge.kind in {EDGE_GIT_TOUCHES, EDGE_GIT_CHANGES_PATH}
        ),
        key=lambda item: (0 if item.kind == EDGE_GIT_TOUCHES else 1, item.id),
    )
    seen_paths: set[str] = set()
    for edge in candidate_edges:
        if edge.source_id != commit_node.id:
            continue
        node = node_map.get(edge.target_id)
        if node is None or node.kind not in {NODE_FILE, NODE_GIT_CHANGED_PATH}:
            continue
        path_key = node.source_ref.path or node.label
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)
        hits.append(
            QueryHit(
                node=node,
                score=100.0 if node.kind == NODE_FILE else 90.0,
                edges=(edge,),
                snippet=_snippet(node),
                explanation=QueryExplanation(
                    matched_fields=(f"edge.{edge.kind}",),
                    score_parts={"git_commit_path": 100.0},
                    exact_match="commit",
                ),
            )
        )
    return QueryResult(
        query=commit_ref,
        hits=tuple(hits[:max_results]),
        omitted=_max_results_omitted(commit_ref, len(hits), max_results),
        diagnostics={"resolution_kind": "static_git_overlay", "commit_ref": commit_ref},
    )


def commits_touching_symbol_file(
    snapshot: GraphSnapshot,
    symbol_node_id: str,
    *,
    max_results: int = 10,
) -> QueryResult:
    """Return recent commits touching the file that owns one symbol node."""
    node = snapshot.node_map().get(symbol_node_id)
    if node is None:
        return QueryResult(
            query=symbol_node_id,
            omitted=(
                OmittedDiagnostic(
                    reason="symbol_not_found",
                    item_id=symbol_node_id,
                ),
            ),
            diagnostics={"resolution_kind": "missing_symbol"},
        )
    path_value = node.source_ref.path
    if not path_value:
        return QueryResult(
            query=symbol_node_id,
            omitted=(
                OmittedDiagnostic(
                    reason="symbol_has_no_source_path",
                    item_id=symbol_node_id,
                ),
            ),
            diagnostics={"resolution_kind": "missing_symbol_path"},
        )
    result = recent_commits_for_path(snapshot, path_value, max_results=max_results)
    return QueryResult(
        query=symbol_node_id,
        hits=result.hits,
        omitted=result.omitted,
        diagnostics={
            **dict(result.diagnostics),
            "symbol_path": path_value,
        },
    )


def _edge_resolution_kind(
    edge: GraphEdge,
    node_map: dict[str, GraphNode],
) -> str:
    if edge.kind in {"depends_on", "references_doc", "references_section"}:
        return "static"
    if edge.kind == "imports":
        return "static" if edge.metadata.get("resolved") is True else "heuristic"
    if edge.kind in {"defines", "parent_symbol", "contains"}:
        return "static"
    if edge.kind in {"calls", "inherits"}:
        source = node_map.get(edge.source_id)
        target = node_map.get(edge.target_id)
        if (
            source is not None
            and target is not None
            and not target.metadata.get("external")
            and source.source_ref.path == target.source_ref.path
        ):
            return "static"
        return "heuristic"
    return "unsupported"


def _resolve_commit_node(
    snapshot: GraphSnapshot,
    commit_ref: str,
) -> GraphNode | None:
    node_map = snapshot.node_map()
    if commit_ref in node_map and node_map[commit_ref].kind == NODE_GIT_COMMIT:
        return node_map[commit_ref]
    matches = [
        node
        for node in snapshot.nodes
        if node.kind == NODE_GIT_COMMIT
        and (
            str(node.metadata.get("commit_hash", "")) == commit_ref
            or str(node.metadata.get("short_commit_hash", "")) == commit_ref
        )
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _git_commit_sort_key(node: GraphNode) -> tuple[int, str, str]:
    committer_epoch = int(node.metadata.get("committer_time_epoch", 0) or 0)
    author_epoch = int(node.metadata.get("author_time_epoch", 0) or 0)
    return (-committer_epoch, -author_epoch, node.id)


def _max_results_omitted(
    item_id: str,
    total: int,
    max_results: int,
) -> tuple[OmittedDiagnostic, ...]:
    if total <= max_results:
        return ()
    return (
        OmittedDiagnostic(
            reason="max_results",
            item_id=item_id,
            details={"omitted": total - max_results},
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
    "backlinks",
    "health",
    "impact",
    "recent_commits_for_path",
    "files_touched_by_commit",
    "commits_touching_symbol_file",
    "neighborhood",
    "path",
    "query",
    "reverse_dependencies",
    "reverse_imports",
]
