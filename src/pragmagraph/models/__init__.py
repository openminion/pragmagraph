"""Immutable DTOs for PragmaGraph observed-fact snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pragmagraph.contracts import INDEXER_VERSION, SCHEMA_VERSION


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _tuple_str(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        text = str(value).strip()
        return (text,) if text else ()
    return tuple(str(item) for item in value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class PragmaGraphError(RuntimeError):
    """Typed package error with a stable code."""

    message: str
    code: str = "PRAGMAGRAPH_ERROR"
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)
        object.__setattr__(self, "details", _frozen_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class SourceRef:
    """Source citation for a node, edge, or query hit."""

    path: str = ""
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    section: str = ""
    uri: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "section": self.section,
            "uri": self.uri,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "SourceRef":
        data = dict(payload or {})
        return cls(
            path=str(data.get("path", "") or ""),
            line=data.get("line"),
            column=data.get("column"),
            end_line=data.get("end_line"),
            end_column=data.get("end_column"),
            section=str(data.get("section", "") or ""),
            uri=str(data.get("uri", "") or ""),
        )


@dataclass(frozen=True)
class GraphNode:
    """One observed graph node."""

    id: str
    kind: str
    label: str
    source_ref: SourceRef = field(default_factory=SourceRef)
    text: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", str(self.id))
        object.__setattr__(self, "kind", str(self.kind))
        object.__setattr__(self, "label", str(self.label))
        object.__setattr__(self, "text", str(self.text or ""))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "source_ref": self.source_ref.to_dict(),
            "text": self.text,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GraphNode":
        return cls(
            id=str(payload["id"]),
            kind=str(payload["kind"]),
            label=str(payload["label"]),
            source_ref=SourceRef.from_dict(payload.get("source_ref")),
            text=str(payload.get("text", "") or ""),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(frozen=True)
class GraphEdge:
    """One observed graph edge."""

    id: str
    kind: str
    source_id: str
    target_id: str
    source_ref: SourceRef = field(default_factory=SourceRef)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", str(self.id))
        object.__setattr__(self, "kind", str(self.kind))
        object.__setattr__(self, "source_id", str(self.source_id))
        object.__setattr__(self, "target_id", str(self.target_id))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_ref": self.source_ref.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GraphEdge":
        return cls(
            id=str(payload["id"]),
            kind=str(payload["kind"]),
            source_id=str(payload["source_id"]),
            target_id=str(payload["target_id"]),
            source_ref=SourceRef.from_dict(payload.get("source_ref")),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(frozen=True)
class OmittedDiagnostic:
    """Reason a candidate fact was omitted from a result."""

    reason: str
    item_id: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", str(self.reason))
        object.__setattr__(self, "item_id", str(self.item_id or ""))
        object.__setattr__(self, "details", _frozen_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "item_id": self.item_id,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OmittedDiagnostic":
        return cls(
            reason=str(payload.get("reason", "") or ""),
            item_id=str(payload.get("item_id", "") or ""),
            details=dict(payload.get("details", {}) or {}),
        )


@dataclass(frozen=True)
class GraphSnapshot:
    """Deterministic JSON snapshot of observed graph facts."""

    namespace: str
    root_path: str
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    omitted: tuple[OmittedDiagnostic, ...] = ()
    stats: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    indexer_version: str = INDEXER_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "namespace", str(self.namespace or "default"))
        object.__setattr__(self, "root_path", str(self.root_path or ""))
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "omitted", tuple(self.omitted))
        object.__setattr__(self, "stats", _frozen_mapping(self.stats))

    def node_map(self) -> dict[str, GraphNode]:
        return {node.id: node for node in self.nodes}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "namespace": self.namespace,
            "root_path": self.root_path,
            "indexer_version": self.indexer_version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "omitted": [item.to_dict() for item in self.omitted],
            "stats": dict(self.stats),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GraphSnapshot":
        return cls(
            schema_version=str(payload.get("schema_version", "") or ""),
            created_at=str(payload.get("created_at", "") or ""),
            namespace=str(payload.get("namespace", "") or "default"),
            root_path=str(payload.get("root_path", "") or ""),
            indexer_version=str(payload.get("indexer_version", "") or ""),
            nodes=tuple(GraphNode.from_dict(item) for item in payload.get("nodes", ())),
            edges=tuple(GraphEdge.from_dict(item) for item in payload.get("edges", ())),
            omitted=tuple(
                OmittedDiagnostic.from_dict(item) for item in payload.get("omitted", ())
            ),
            stats=dict(payload.get("stats", {}) or {}),
        )


@dataclass(frozen=True)
class QueryRequest:
    """Query request over a snapshot."""

    query: str = ""
    node_ids: tuple[str, ...] = ()
    max_results: int = 10
    include_edges: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "query", str(self.query or ""))
        object.__setattr__(self, "node_ids", _tuple_str(self.node_ids))
        object.__setattr__(self, "max_results", max(1, int(self.max_results or 1)))


@dataclass(frozen=True)
class QueryHit:
    """One cited query hit."""

    node: GraphNode
    score: float
    edges: tuple[GraphEdge, ...] = ()
    snippet: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "snippet", str(self.snippet or ""))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node.to_dict(),
            "score": self.score,
            "edges": [edge.to_dict() for edge in self.edges],
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class QueryResult:
    """Cited query result."""

    query: str
    hits: tuple[QueryHit, ...] = ()
    omitted: tuple[OmittedDiagnostic, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "hits", tuple(self.hits))
        object.__setattr__(self, "omitted", tuple(self.omitted))
        object.__setattr__(self, "diagnostics", _frozen_mapping(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "hits": [hit.to_dict() for hit in self.hits],
            "omitted": [item.to_dict() for item in self.omitted],
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class PathResult:
    """Bounded path result between two graph nodes."""

    source_id: str
    target_id: str
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    omitted: tuple[OmittedDiagnostic, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "omitted": [item.to_dict() for item in self.omitted],
        }


@dataclass(frozen=True)
class HealthSummary:
    """Snapshot health/freshness summary."""

    ok: bool
    schema_version: str
    namespace: str
    node_count: int
    edge_count: int
    omitted_count: int
    stats: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stats", _frozen_mapping(self.stats))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "schema_version": self.schema_version,
            "namespace": self.namespace,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "omitted_count": self.omitted_count,
            "stats": dict(self.stats),
        }


__all__ = [
    "GraphEdge",
    "GraphNode",
    "GraphSnapshot",
    "HealthSummary",
    "OmittedDiagnostic",
    "PathResult",
    "PragmaGraphError",
    "QueryHit",
    "QueryRequest",
    "QueryResult",
    "SourceRef",
]
