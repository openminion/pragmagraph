"""Structural topology summaries for observed snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping
from pragmagraph.models import GraphNode, GraphSnapshot, SourceRef


@dataclass(frozen=True)
class TopologyNode:
    """One node-level topology fact."""

    node_id: str
    kind: str
    label: str
    degree: int
    incoming_degree: int = 0
    outgoing_degree: int = 0
    source_ref: SourceRef = field(default_factory=SourceRef)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "label": self.label,
            "degree": self.degree,
            "incoming_degree": self.incoming_degree,
            "outgoing_degree": self.outgoing_degree,
            "source_ref": self.source_ref.to_dict(),
        }


@dataclass(frozen=True)
class TopologyComponent:
    """One connected component summary."""

    component_id: str
    node_count: int
    edge_count: int
    representative_node_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "representative_node_ids", tuple(self.representative_node_ids)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "representative_node_ids": list(self.representative_node_ids),
        }


@dataclass(frozen=True)
class TopologySummary:
    """Observed structural topology summary."""

    namespace: str
    node_count: int
    edge_count: int
    component_count: int
    isolated_count: int
    high_degree_nodes: tuple[TopologyNode, ...] = ()
    isolated_nodes: tuple[TopologyNode, ...] = ()
    components: tuple[TopologyComponent, ...] = ()
    node_kinds: Mapping[str, int] = field(default_factory=dict)
    edge_kinds: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "high_degree_nodes", tuple(self.high_degree_nodes))
        object.__setattr__(self, "isolated_nodes", tuple(self.isolated_nodes))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(self, "node_kinds", frozen_mapping(self.node_kinds))
        object.__setattr__(self, "edge_kinds", frozen_mapping(self.edge_kinds))

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "component_count": self.component_count,
            "isolated_count": self.isolated_count,
            "high_degree_nodes": [item.to_dict() for item in self.high_degree_nodes],
            "isolated_nodes": [item.to_dict() for item in self.isolated_nodes],
            "components": [item.to_dict() for item in self.components],
            "node_kinds": dict(self.node_kinds),
            "edge_kinds": dict(self.edge_kinds),
        }


def build_topology_summary(
    snapshot: GraphSnapshot,
    *,
    top_n: int = 10,
) -> TopologySummary:
    """Return deterministic degree and component facts for ``snapshot``."""
    limit = max(1, int(top_n or 1))
    incoming: Counter[str] = Counter(edge.target_id for edge in snapshot.edges)
    outgoing: Counter[str] = Counter(edge.source_id for edge in snapshot.edges)
    degree = incoming + outgoing
    nodes = {node.id: node for node in snapshot.nodes}
    ranked = sorted(
        snapshot.nodes,
        key=lambda node: (
            -(degree[node.id]),
            node.kind,
            node.source_ref.path,
            node.id,
        ),
    )
    isolated = [node for node in ranked if degree[node.id] == 0]
    components = _components(snapshot, nodes)
    return TopologySummary(
        namespace=snapshot.namespace,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        component_count=len(components),
        isolated_count=len(isolated),
        high_degree_nodes=tuple(
            _topology_node(node, degree, incoming, outgoing) for node in ranked[:limit]
        ),
        isolated_nodes=tuple(
            _topology_node(node, degree, incoming, outgoing)
            for node in isolated[:limit]
        ),
        components=tuple(components[:limit]),
        node_kinds=dict(Counter(node.kind for node in snapshot.nodes)),
        edge_kinds=dict(Counter(edge.kind for edge in snapshot.edges)),
    )


def render_markdown_topology(summary: TopologySummary) -> str:
    """Render a structural topology summary as Markdown."""
    lines = [
        "# PragmaGraph Topology",
        "",
        f"- Namespace: `{summary.namespace}`",
        f"- Nodes / edges: `{summary.node_count}` / `{summary.edge_count}`",
        f"- Components: `{summary.component_count}`",
        f"- Isolated nodes: `{summary.isolated_count}`",
        "",
        "## High-Degree Nodes",
        "",
    ]
    lines.extend(
        f"- `{node.node_id}` ({node.kind}, degree {node.degree})"
        for node in summary.high_degree_nodes
    )
    if summary.isolated_nodes:
        lines.extend(["", "## Isolated Nodes", ""])
        lines.extend(
            f"- `{node.node_id}` ({node.kind})" for node in summary.isolated_nodes
        )
    return "\n".join(lines).rstrip() + "\n"


def _topology_node(
    node: GraphNode,
    degree: Counter[str],
    incoming: Counter[str],
    outgoing: Counter[str],
) -> TopologyNode:
    return TopologyNode(
        node_id=node.id,
        kind=node.kind,
        label=node.label,
        degree=degree[node.id],
        incoming_degree=incoming[node.id],
        outgoing_degree=outgoing[node.id],
        source_ref=node.source_ref,
    )


def _components(
    snapshot: GraphSnapshot,
    nodes: Mapping[str, GraphNode],
) -> list[TopologyComponent]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    edge_counts: Counter[str] = Counter()
    for edge in snapshot.edges:
        adjacency[edge.source_id].add(edge.target_id)
        adjacency[edge.target_id].add(edge.source_id)
    visited: set[str] = set()
    components: list[TopologyComponent] = []
    for node_id in sorted(nodes):
        if node_id in visited:
            continue
        queue: deque[str] = deque([node_id])
        visited.add(node_id)
        members: set[str] = set()
        while queue:
            current = queue.popleft()
            members.add(current)
            for other in sorted(adjacency[current]):
                if other not in visited:
                    visited.add(other)
                    queue.append(other)
        component_id = min(members)
        for edge in snapshot.edges:
            if edge.source_id in members and edge.target_id in members:
                edge_counts[component_id] += 1
        components.append(
            TopologyComponent(
                component_id=component_id,
                node_count=len(members),
                edge_count=edge_counts[component_id],
                representative_node_ids=tuple(sorted(members)[:5]),
            )
        )
    components.sort(
        key=lambda item: (-item.node_count, -item.edge_count, item.component_id)
    )
    return components


__all__ = [
    "TopologyComponent",
    "TopologyNode",
    "TopologySummary",
    "build_topology_summary",
    "render_markdown_topology",
]
