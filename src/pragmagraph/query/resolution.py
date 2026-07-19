"""Read-only navigation over exact cross-repository resolution facts."""

from __future__ import annotations

from pragmagraph.contracts import (
    EDGE_RESOLVES_TO,
    RESOLUTION_KIND_EXACT_SCIP_SYMBOL,
)
from pragmagraph.models import GraphNode, GraphSnapshot, OmittedDiagnostic


def resolved_definition(
    snapshot: GraphSnapshot,
    external_node_id: str,
) -> GraphNode | None:
    """Return the one recorded exact definition for an external node."""
    targets = {
        edge.target_id
        for edge in snapshot.edges
        if edge.kind == EDGE_RESOLVES_TO
        and edge.source_id == external_node_id
        and edge.metadata.get("resolution_kind") == RESOLUTION_KIND_EXACT_SCIP_SYMBOL
    }
    if len(targets) != 1:
        return None
    return snapshot.node_map().get(next(iter(targets)))


def incoming_external_symbols(
    snapshot: GraphSnapshot,
    definition_node_id: str,
    *,
    max_results: int = 100,
) -> tuple[GraphNode, ...]:
    """List external symbols with recorded edges to one exact definition."""
    limit = max(1, int(max_results))
    source_ids = {
        edge.source_id
        for edge in snapshot.edges
        if edge.kind == EDGE_RESOLVES_TO
        and edge.target_id == definition_node_id
        and edge.metadata.get("resolution_kind") == RESOLUTION_KIND_EXACT_SCIP_SYMBOL
    }
    nodes = snapshot.node_map()
    return tuple(
        nodes[node_id] for node_id in sorted(source_ids)[:limit] if node_id in nodes
    )


def cross_repo_resolution_diagnostics(
    snapshot: GraphSnapshot,
    *,
    reason: str = "",
    max_results: int = 100,
) -> tuple[OmittedDiagnostic, ...]:
    """Return bounded recorded resolution diagnostics without re-resolving."""
    limit = max(1, int(max_results))
    prefix = "cross_repo_"
    return tuple(
        item
        for item in sorted(
            snapshot.omitted, key=lambda value: (value.reason, value.item_id)
        )
        if item.reason.startswith(prefix) and (not reason or item.reason == reason)
    )[:limit]


__all__ = [
    "cross_repo_resolution_diagnostics",
    "incoming_external_symbols",
    "resolved_definition",
]
