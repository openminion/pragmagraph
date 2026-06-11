"""Deterministic structural reports for PragmaGraph snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pragmagraph.contracts import (
    EDGE_DEPENDS_ON,
    NODE_DOC_SECTION,
    NODE_PYTHON_CLASS,
    NODE_PYTHON_FUNCTION,
    NODE_PYTHON_METHOD,
)
from pragmagraph.models import GraphNode, GraphSnapshot, OmittedDiagnostic, SourceRef


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _tuple_str(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        text = str(value).strip()
        return (text,) if text else ()
    return tuple(str(item) for item in value)  # type: ignore[arg-type]


def _source_ref_payload(source_ref: SourceRef) -> dict[str, Any]:
    return source_ref.to_dict()


@dataclass(frozen=True)
class GraphReportSummary:
    """Top-level deterministic counts for one snapshot report."""

    namespace: str
    root_path: str
    schema_version: str
    indexer_version: str
    node_count: int
    edge_count: int
    omitted_count: int
    dependency_count: int = 0
    config_count: int = 0
    node_kinds: Mapping[str, int] = field(default_factory=dict)
    edge_kinds: Mapping[str, int] = field(default_factory=dict)
    omitted_reasons: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_kinds", _frozen_mapping(self.node_kinds))
        object.__setattr__(self, "edge_kinds", _frozen_mapping(self.edge_kinds))
        object.__setattr__(
            self, "omitted_reasons", _frozen_mapping(self.omitted_reasons)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "root_path": self.root_path,
            "schema_version": self.schema_version,
            "indexer_version": self.indexer_version,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "omitted_count": self.omitted_count,
            "dependency_count": self.dependency_count,
            "config_count": self.config_count,
            "node_kinds": dict(self.node_kinds),
            "edge_kinds": dict(self.edge_kinds),
            "omitted_reasons": dict(self.omitted_reasons),
        }


@dataclass(frozen=True)
class GraphReportNode:
    """Node-level structural ranking entry."""

    node_id: str
    kind: str
    label: str
    source_ref: SourceRef = field(default_factory=SourceRef)
    degree: int = 0
    incoming_degree: int = 0
    outgoing_degree: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "label": self.label,
            "source_ref": _source_ref_payload(self.source_ref),
            "degree": self.degree,
            "incoming_degree": self.incoming_degree,
            "outgoing_degree": self.outgoing_degree,
        }


@dataclass(frozen=True)
class GraphReportFinding:
    """One structural finding or unresolved fact."""

    category: str
    item_id: str
    label: str = ""
    source_ref: SourceRef = field(default_factory=SourceRef)
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _frozen_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "item_id": self.item_id,
            "label": self.label,
            "source_ref": _source_ref_payload(self.source_ref),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class GraphReportDependency:
    """Declared dependency extracted from config metadata."""

    config_path: str
    dependency: str
    node_id: str
    source_ref: SourceRef = field(default_factory=SourceRef)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "dependency": self.dependency,
            "node_id": self.node_id,
            "source_ref": _source_ref_payload(self.source_ref),
        }


@dataclass(frozen=True)
class GraphReport:
    """Deterministic structural report over a graph snapshot."""

    summary: GraphReportSummary
    top_nodes: tuple[GraphReportNode, ...] = ()
    hotspots: tuple[GraphReportNode, ...] = ()
    orphan_nodes: tuple[GraphReportFinding, ...] = ()
    unresolved_items: tuple[GraphReportFinding, ...] = ()
    dependencies: tuple[GraphReportDependency, ...] = ()
    structural_summary: tuple[str, ...] = ()
    suggested_queries: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "top_nodes", tuple(self.top_nodes))
        object.__setattr__(self, "hotspots", tuple(self.hotspots))
        object.__setattr__(self, "orphan_nodes", tuple(self.orphan_nodes))
        object.__setattr__(self, "unresolved_items", tuple(self.unresolved_items))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(
            self, "structural_summary", _tuple_str(self.structural_summary)
        )
        object.__setattr__(
            self, "suggested_queries", _tuple_str(self.suggested_queries)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "top_nodes": [item.to_dict() for item in self.top_nodes],
            "hotspots": [item.to_dict() for item in self.hotspots],
            "orphan_nodes": [item.to_dict() for item in self.orphan_nodes],
            "unresolved_items": [item.to_dict() for item in self.unresolved_items],
            "dependencies": [item.to_dict() for item in self.dependencies],
            "structural_summary": list(self.structural_summary),
            "suggested_queries": list(self.suggested_queries),
        }


def build_report(snapshot: GraphSnapshot, *, top_n: int = 10) -> GraphReport:
    """Build a deterministic structural report from ``snapshot``."""
    node_kinds = _count_by_kind(node.kind for node in snapshot.nodes)
    edge_kinds = _count_by_kind(edge.kind for edge in snapshot.edges)
    omitted_reasons = _count_by_kind(item.reason for item in snapshot.omitted)
    incoming_degree, outgoing_degree = _degree_maps(snapshot)
    node_map = snapshot.node_map()

    ranked_nodes = sorted(
        snapshot.nodes,
        key=lambda node: (
            -(incoming_degree.get(node.id, 0) + outgoing_degree.get(node.id, 0)),
            -outgoing_degree.get(node.id, 0),
            node.kind,
            node.source_ref.path,
            node.id,
        ),
    )
    top_nodes = tuple(
        GraphReportNode(
            node_id=node.id,
            kind=node.kind,
            label=node.label,
            source_ref=node.source_ref,
            degree=incoming_degree.get(node.id, 0) + outgoing_degree.get(node.id, 0),
            incoming_degree=incoming_degree.get(node.id, 0),
            outgoing_degree=outgoing_degree.get(node.id, 0),
        )
        for node in ranked_nodes[: max(1, top_n)]
    )
    orphan_nodes = tuple(
        GraphReportFinding(
            category="orphan_node",
            item_id=node.id,
            label=node.label,
            source_ref=node.source_ref,
            details={"kind": node.kind},
        )
        for node in sorted(
            snapshot.nodes,
            key=lambda item: (item.kind, item.source_ref.path, item.id),
        )
        if incoming_degree.get(node.id, 0) + outgoing_degree.get(node.id, 0) == 0
    )
    unresolved_items = tuple(_finding_from_omitted(item) for item in snapshot.omitted)
    dependencies = _dependencies(snapshot, node_map)
    structural_summary = _structural_summary(
        top_nodes=top_nodes,
        orphan_nodes=orphan_nodes,
        unresolved_items=unresolved_items,
        dependencies=dependencies,
    )
    suggested_queries = _suggested_queries(snapshot, dependencies, unresolved_items)

    return GraphReport(
        summary=GraphReportSummary(
            namespace=snapshot.namespace,
            root_path=snapshot.root_path,
            schema_version=snapshot.schema_version,
            indexer_version=snapshot.indexer_version,
            node_count=len(snapshot.nodes),
            edge_count=len(snapshot.edges),
            omitted_count=len(snapshot.omitted),
            dependency_count=len(dependencies),
            config_count=sum(1 for node in snapshot.nodes if node.kind == "config"),
            node_kinds=node_kinds,
            edge_kinds=edge_kinds,
            omitted_reasons=omitted_reasons,
        ),
        top_nodes=top_nodes,
        hotspots=top_nodes,
        orphan_nodes=orphan_nodes,
        unresolved_items=unresolved_items,
        dependencies=dependencies,
        structural_summary=structural_summary,
        suggested_queries=suggested_queries,
    )


def render_markdown_report(report: GraphReport) -> str:
    """Render ``report`` as deterministic Markdown."""
    summary = report.summary
    lines = [
        "# PragmaGraph Structural Report",
        "",
        f"- Namespace: `{summary.namespace}`",
        f"- Root path: `{summary.root_path}`",
        f"- Schema version: `{summary.schema_version}`",
        f"- Indexer version: `{summary.indexer_version}`",
        f"- Node count: `{summary.node_count}`",
        f"- Edge count: `{summary.edge_count}`",
        f"- Omitted count: `{summary.omitted_count}`",
        f"- Dependency count: `{summary.dependency_count}`",
        f"- Config count: `{summary.config_count}`",
        "",
        "## Node Kinds",
        "",
    ]
    lines.extend(_markdown_count_lines(summary.node_kinds))
    lines.extend(["", "## Edge Kinds", ""])
    lines.extend(_markdown_count_lines(summary.edge_kinds))
    lines.extend(["", "## Omitted Reasons", ""])
    lines.extend(_markdown_count_lines(summary.omitted_reasons))
    lines.extend(["", "## Hotspots", ""])
    if report.hotspots:
        for item in report.hotspots:
            path = item.source_ref.path or item.node_id
            lines.append(
                f"- `{item.label}` ({item.kind}) in `{path}` "
                f"[degree={item.degree}, in={item.incoming_degree}, out={item.outgoing_degree}]"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Dependencies", ""])
    if report.dependencies:
        for item in report.dependencies:
            lines.append(f"- `{item.dependency}` declared by `{item.config_path}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Unresolved Items", ""])
    if report.unresolved_items:
        for item in report.unresolved_items:
            path = item.source_ref.path or str(item.details.get("source_path") or "")
            suffix = f" via `{path}`" if path else ""
            lines.append(f"- `{item.category}`: `{item.item_id}`{suffix}")
    else:
        lines.append("- none")
    lines.extend(["", "## Structural Summary", ""])
    if report.structural_summary:
        for item in report.structural_summary:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## Suggested Queries", ""])
    if report.suggested_queries:
        for item in report.suggested_queries:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _count_by_kind(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _degree_maps(snapshot: GraphSnapshot) -> tuple[dict[str, int], dict[str, int]]:
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    for edge in snapshot.edges:
        outgoing[edge.source_id] = outgoing.get(edge.source_id, 0) + 1
        incoming[edge.target_id] = incoming.get(edge.target_id, 0) + 1
    return incoming, outgoing


def _finding_from_omitted(item: OmittedDiagnostic) -> GraphReportFinding:
    details = dict(item.details)
    path = str(details.get("source_path", "") or "")
    line = details.get("line")
    return GraphReportFinding(
        category=item.reason,
        item_id=item.item_id,
        label=item.item_id,
        source_ref=SourceRef(path=path, line=line),
        details=details,
    )


def _dependencies(
    snapshot: GraphSnapshot,
    node_map: Mapping[str, GraphNode],
) -> tuple[GraphReportDependency, ...]:
    items: list[GraphReportDependency] = []
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if edge.kind != EDGE_DEPENDS_ON:
            continue
        source = node_map.get(edge.source_id)
        target = node_map.get(edge.target_id)
        if source is None or target is None:
            continue
        items.append(
            GraphReportDependency(
                config_path=source.source_ref.path or source.label,
                dependency=target.label,
                node_id=target.id,
                source_ref=target.source_ref,
            )
        )
    return tuple(items)


def _suggested_queries(
    snapshot: GraphSnapshot,
    dependencies: tuple[GraphReportDependency, ...],
    unresolved_items: tuple[GraphReportFinding, ...],
) -> tuple[str, ...]:
    suggestions: list[str] = []
    preferred_kinds = (
        NODE_PYTHON_CLASS,
        NODE_PYTHON_FUNCTION,
        NODE_PYTHON_METHOD,
        NODE_DOC_SECTION,
    )
    for kind in preferred_kinds:
        node = next((item for item in snapshot.nodes if item.kind == kind), None)
        if node is None:
            continue
        if kind == NODE_DOC_SECTION:
            suggestions.append(f"Which files link to `{node.label}`?")
            continue
        suggestions.append(f"Who calls `{node.label}`?")
        suggestions.append(f"Where is `{node.label}` defined?")
        break
    if dependencies:
        suggestions.append(
            f"What package dependencies are declared in `{dependencies[0].config_path}`?"
        )
    if any(item.category.startswith("unresolved_") for item in unresolved_items):
        suggestions.append("What unresolved imports or doc links exist?")
    return tuple(dict.fromkeys(suggestions))


def _structural_summary(
    *,
    top_nodes: tuple[GraphReportNode, ...],
    orphan_nodes: tuple[GraphReportFinding, ...],
    unresolved_items: tuple[GraphReportFinding, ...],
    dependencies: tuple[GraphReportDependency, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    if top_nodes:
        first = top_nodes[0]
        lines.append(
            f"Top hotspot by graph degree is `{first.label}` with degree {first.degree}."
        )
    lines.append(f"Orphan node count: {len(orphan_nodes)}.")
    lines.append(f"Unresolved structural item count: {len(unresolved_items)}.")
    lines.append(f"Declared dependency count: {len(dependencies)}.")
    return tuple(lines)


def _markdown_count_lines(counts: Mapping[str, int]) -> list[str]:
    if not counts:
        return ["- none"]
    return [f"- `{key}`: `{value}`" for key, value in counts.items()]


__all__ = [
    "GraphReport",
    "GraphReportDependency",
    "GraphReportFinding",
    "GraphReportNode",
    "GraphReportSummary",
    "build_report",
    "render_markdown_report",
]
