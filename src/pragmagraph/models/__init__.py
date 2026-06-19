"""Immutable DTOs for PragmaGraph observed-fact snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping, tuple_str
from pragmagraph.contracts import INDEXER_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class PragmaGraphError(RuntimeError):
    """Typed package error with a stable code."""

    message: str
    code: str = "PRAGMAGRAPH_ERROR"
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)
        object.__setattr__(self, "details", frozen_mapping(self.details))

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
        object.__setattr__(self, "metadata", frozen_mapping(self.metadata))

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
        object.__setattr__(self, "metadata", frozen_mapping(self.metadata))

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
        object.__setattr__(self, "details", frozen_mapping(self.details))

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
class ParserDiagnostic:
    """Typed diagnostic emitted by a parser or scope policy."""

    code: str
    message: str
    path: str = ""
    line: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", str(self.code))
        object.__setattr__(self, "message", str(self.message))
        object.__setattr__(self, "path", str(self.path or ""))
        object.__setattr__(self, "details", frozen_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ParserDiagnostic":
        return cls(
            code=str(payload.get("code", "") or ""),
            message=str(payload.get("message", "") or ""),
            path=str(payload.get("path", "") or ""),
            line=payload.get("line"),
            details=dict(payload.get("details", {}) or {}),
        )


@dataclass(frozen=True)
class ParserResult:
    """Facts extracted from one file by a parser."""

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    diagnostics: tuple[ParserDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


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
        object.__setattr__(self, "stats", frozen_mapping(self.stats))

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
        object.__setattr__(self, "node_ids", tuple_str(self.node_ids))
        object.__setattr__(self, "max_results", max(1, int(self.max_results or 1)))


@dataclass(frozen=True)
class QueryExplanation:
    """Why a query hit scored the way it did."""

    matched_fields: tuple[str, ...] = ()
    matched_tokens: tuple[str, ...] = ()
    exact_match: str = ""
    score_parts: Mapping[str, float] = field(default_factory=dict)
    omitted_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "matched_fields", tuple_str(self.matched_fields))
        object.__setattr__(self, "matched_tokens", tuple_str(self.matched_tokens))
        object.__setattr__(self, "exact_match", str(self.exact_match or ""))
        object.__setattr__(
            self,
            "score_parts",
            MappingProxyType(
                {str(key): float(value) for key, value in self.score_parts.items()}
            ),
        )
        object.__setattr__(self, "omitted_reasons", tuple_str(self.omitted_reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_fields": list(self.matched_fields),
            "matched_tokens": list(self.matched_tokens),
            "exact_match": self.exact_match,
            "score_parts": dict(self.score_parts),
            "omitted_reasons": list(self.omitted_reasons),
        }


@dataclass(frozen=True)
class QueryHit:
    """One cited query hit."""

    node: GraphNode
    score: float
    edges: tuple[GraphEdge, ...] = ()
    snippet: str = ""
    explanation: QueryExplanation = field(default_factory=QueryExplanation)

    def __post_init__(self) -> None:
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "snippet", str(self.snippet or ""))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node.to_dict(),
            "score": self.score,
            "edges": [edge.to_dict() for edge in self.edges],
            "snippet": self.snippet,
            "explanation": self.explanation.to_dict(),
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
        object.__setattr__(self, "diagnostics", frozen_mapping(self.diagnostics))

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
        object.__setattr__(self, "stats", frozen_mapping(self.stats))

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


@dataclass(frozen=True)
class RefreshManifestEntry:
    """Content-hash manifest row for one indexed file."""

    path: str
    content_hash: str
    parser: str = ""
    parser_version: str = ""
    size_bytes: int = 0
    file_kind: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", str(self.path))
        object.__setattr__(self, "content_hash", str(self.content_hash))
        object.__setattr__(self, "parser", str(self.parser or ""))
        object.__setattr__(self, "parser_version", str(self.parser_version or ""))
        object.__setattr__(self, "size_bytes", max(0, int(self.size_bytes or 0)))
        object.__setattr__(self, "file_kind", str(self.file_kind or ""))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "parser": self.parser,
            "parser_version": self.parser_version,
            "size_bytes": self.size_bytes,
            "file_kind": self.file_kind,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RefreshManifestEntry":
        return cls(
            path=str(payload.get("path", "") or ""),
            content_hash=str(payload.get("content_hash", "") or ""),
            parser=str(payload.get("parser", "") or ""),
            parser_version=str(payload.get("parser_version", "") or ""),
            size_bytes=int(payload.get("size_bytes", 0) or 0),
            file_kind=str(payload.get("file_kind", "") or ""),
        )


@dataclass(frozen=True)
class RefreshManifest:
    """Deterministic content manifest used by refresh operations."""

    schema_version: str = "pragmagraph.refresh_manifest.v2alpha1"
    root_path: str = ""
    entries: tuple[RefreshManifestEntry, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", str(self.schema_version or ""))
        object.__setattr__(self, "root_path", str(self.root_path or ""))
        object.__setattr__(
            self,
            "entries",
            tuple(sorted(self.entries, key=lambda item: item.path)),
        )

    def by_path(self) -> dict[str, RefreshManifestEntry]:
        return {entry.path: entry for entry in self.entries}

    def parser_versions(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    f"{entry.parser}:{entry.parser_version}"
                    for entry in self.entries
                    if entry.parser
                }
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root_path": self.root_path,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "RefreshManifest":
        return cls(
            schema_version=str((payload or {}).get("schema_version", "") or ""),
            root_path=str((payload or {}).get("root_path", "") or ""),
            entries=tuple(
                RefreshManifestEntry.from_dict(item)
                for item in (payload or {}).get("entries", ())
            ),
        )


@dataclass(frozen=True)
class RefreshPathChange:
    """Deterministic per-path refresh status."""

    path: str
    status: str
    reasons: tuple[str, ...] = ()
    previous_entry: RefreshManifestEntry | None = None
    current_entry: RefreshManifestEntry | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", str(self.path or ""))
        object.__setattr__(self, "status", str(self.status or ""))
        object.__setattr__(self, "reasons", tuple_str(self.reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "reasons": list(self.reasons),
            "previous_entry": (
                self.previous_entry.to_dict()
                if self.previous_entry is not None
                else None
            ),
            "current_entry": (
                self.current_entry.to_dict() if self.current_entry is not None else None
            ),
        }


@dataclass(frozen=True)
class SnapshotStructuralDelta:
    """Structural delta between two deterministic snapshots."""

    added_node_ids: tuple[str, ...] = ()
    removed_node_ids: tuple[str, ...] = ()
    added_edge_ids: tuple[str, ...] = ()
    removed_edge_ids: tuple[str, ...] = ()
    added_omitted_ids: tuple[str, ...] = ()
    removed_omitted_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "added_node_ids", tuple_str(self.added_node_ids))
        object.__setattr__(self, "removed_node_ids", tuple_str(self.removed_node_ids))
        object.__setattr__(self, "added_edge_ids", tuple_str(self.added_edge_ids))
        object.__setattr__(self, "removed_edge_ids", tuple_str(self.removed_edge_ids))
        object.__setattr__(self, "added_omitted_ids", tuple_str(self.added_omitted_ids))
        object.__setattr__(
            self, "removed_omitted_ids", tuple_str(self.removed_omitted_ids)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_node_ids": list(self.added_node_ids),
            "removed_node_ids": list(self.removed_node_ids),
            "added_edge_ids": list(self.added_edge_ids),
            "removed_edge_ids": list(self.removed_edge_ids),
            "added_omitted_ids": list(self.added_omitted_ids),
            "removed_omitted_ids": list(self.removed_omitted_ids),
        }


@dataclass(frozen=True)
class RefreshResult:
    """Result of refreshing a graph snapshot."""

    snapshot: GraphSnapshot
    manifest: RefreshManifest
    changed_paths: tuple[str, ...] = ()
    unchanged_paths: tuple[str, ...] = ()
    removed_paths: tuple[str, ...] = ()
    path_changes: tuple[RefreshPathChange, ...] = ()
    snapshot_delta: SnapshotStructuralDelta = field(
        default_factory=SnapshotStructuralDelta
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "changed_paths", tuple_str(self.changed_paths))
        object.__setattr__(self, "unchanged_paths", tuple_str(self.unchanged_paths))
        object.__setattr__(self, "removed_paths", tuple_str(self.removed_paths))
        object.__setattr__(self, "path_changes", tuple(self.path_changes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "manifest": self.manifest.to_dict(),
            "changed_paths": list(self.changed_paths),
            "unchanged_paths": list(self.unchanged_paths),
            "removed_paths": list(self.removed_paths),
            "path_changes": [item.to_dict() for item in self.path_changes],
            "snapshot_delta": self.snapshot_delta.to_dict(),
        }


__all__ = [
    "GraphEdge",
    "GraphNode",
    "GraphSnapshot",
    "HealthSummary",
    "OmittedDiagnostic",
    "PathResult",
    "ParserDiagnostic",
    "ParserResult",
    "PragmaGraphError",
    "QueryExplanation",
    "QueryHit",
    "QueryRequest",
    "QueryResult",
    "RefreshManifest",
    "RefreshManifestEntry",
    "RefreshPathChange",
    "RefreshResult",
    "SnapshotStructuralDelta",
    "SourceRef",
]
