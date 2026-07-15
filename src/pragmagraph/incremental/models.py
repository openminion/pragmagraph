"""Internal deterministic cache models for incremental indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph.models import GraphEdge, GraphNode, OmittedDiagnostic, PragmaGraphError
from pragmagraph._immutables import frozen_mapping


CACHE_SCHEMA_VERSION = "pragmagraph.extraction_cache.v1alpha1"


@dataclass(frozen=True)
class FileIndexFragment:
    """Observed facts extracted from one source file before global resolution."""

    path: str
    content_hash: str
    parser: str = ""
    parser_version: str = ""
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    omitted: tuple[OmittedDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "omitted", tuple(self.omitted))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "parser": self.parser,
            "parser_version": self.parser_version,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "omitted": [item.to_dict() for item in self.omitted],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FileIndexFragment":
        return cls(
            path=str(payload.get("path", "") or ""),
            content_hash=str(payload.get("content_hash", "") or ""),
            parser=str(payload.get("parser", "") or ""),
            parser_version=str(payload.get("parser_version", "") or ""),
            nodes=tuple(GraphNode.from_dict(item) for item in payload.get("nodes", ())),
            edges=tuple(GraphEdge.from_dict(item) for item in payload.get("edges", ())),
            omitted=tuple(
                OmittedDiagnostic.from_dict(item) for item in payload.get("omitted", ())
            ),
        )


@dataclass(frozen=True)
class CacheFingerprint:
    """Inputs that determine whether file fragments remain reusable."""

    snapshot_schema: str
    indexer_version: str
    namespace: str
    root_identity: str
    policy_hash: str
    ignore_hash: str
    parser_signature: str
    git_identity_mode: str
    git_repository: str = ""
    git_head: str = ""
    git_shallow: bool = False
    file_set_hash: str = ""
    git_history_contract: str = "pragmagraph.git_history.v1alpha1"

    def extraction_key(self) -> tuple[str, ...]:
        """Return fields that affect source-file extraction."""
        return (
            self.snapshot_schema,
            self.indexer_version,
            self.namespace,
            self.root_identity,
            self.policy_hash,
            self.ignore_hash,
            self.parser_signature,
        )

    def git_key(self) -> tuple[str, ...]:
        """Return fields that affect the repository-wide git overlay."""
        return (
            self.git_identity_mode,
            self.git_repository,
            self.git_head,
            str(self.git_shallow),
            self.file_set_hash,
            self.git_history_contract,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_schema": self.snapshot_schema,
            "indexer_version": self.indexer_version,
            "namespace": self.namespace,
            "root_identity": self.root_identity,
            "policy_hash": self.policy_hash,
            "ignore_hash": self.ignore_hash,
            "parser_signature": self.parser_signature,
            "git_identity_mode": self.git_identity_mode,
            "git_repository": self.git_repository,
            "git_head": self.git_head,
            "git_shallow": self.git_shallow,
            "file_set_hash": self.file_set_hash,
            "git_history_contract": self.git_history_contract,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CacheFingerprint":
        return cls(
            snapshot_schema=str(payload.get("snapshot_schema", "") or ""),
            indexer_version=str(payload.get("indexer_version", "") or ""),
            namespace=str(payload.get("namespace", "") or ""),
            root_identity=str(payload.get("root_identity", "") or ""),
            policy_hash=str(payload.get("policy_hash", "") or ""),
            ignore_hash=str(payload.get("ignore_hash", "") or ""),
            parser_signature=str(payload.get("parser_signature", "") or ""),
            git_identity_mode=str(payload.get("git_identity_mode", "") or ""),
            git_repository=str(payload.get("git_repository", "") or ""),
            git_head=str(payload.get("git_head", "") or ""),
            git_shallow=bool(payload.get("git_shallow", False)),
            file_set_hash=str(payload.get("file_set_hash", "") or ""),
            git_history_contract=str(
                payload.get("git_history_contract", "")
                or "pragmagraph.git_history.v1alpha1"
            ),
        )


@dataclass(frozen=True)
class ExtractionCacheBundle:
    """One rebuildable current cache for file-owned extraction facts."""

    fingerprint: CacheFingerprint
    fragments: tuple[FileIndexFragment, ...] = ()
    git_nodes: tuple[GraphNode, ...] = ()
    git_edges: tuple[GraphEdge, ...] = ()
    git_omitted: tuple[OmittedDiagnostic, ...] = ()
    git_stats: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = CACHE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fragments",
            tuple(sorted(self.fragments, key=lambda item: item.path)),
        )
        object.__setattr__(self, "git_nodes", tuple(self.git_nodes))
        object.__setattr__(self, "git_edges", tuple(self.git_edges))
        object.__setattr__(self, "git_omitted", tuple(self.git_omitted))
        object.__setattr__(self, "git_stats", frozen_mapping(self.git_stats or {}))

    def by_path(self) -> dict[str, FileIndexFragment]:
        return {item.path: item for item in self.fragments}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint.to_dict(),
            "fragments": [item.to_dict() for item in self.fragments],
            "git_nodes": [item.to_dict() for item in self.git_nodes],
            "git_edges": [item.to_dict() for item in self.git_edges],
            "git_omitted": [item.to_dict() for item in self.git_omitted],
            "git_stats": dict(self.git_stats),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExtractionCacheBundle":
        version = str(payload.get("schema_version", "") or "")
        if version != CACHE_SCHEMA_VERSION:
            raise PragmaGraphError(
                "unsupported extraction cache schema",
                code="EXTRACTION_CACHE_INCOMPATIBLE",
                details={"expected": CACHE_SCHEMA_VERSION, "actual": version},
            )
        fingerprint = payload.get("fingerprint", {})
        if not isinstance(fingerprint, Mapping):
            raise PragmaGraphError(
                "extraction cache fingerprint must be an object",
                code="INVALID_EXTRACTION_CACHE",
            )
        return cls(
            schema_version=version,
            fingerprint=CacheFingerprint.from_dict(fingerprint),
            fragments=tuple(
                FileIndexFragment.from_dict(item)
                for item in payload.get("fragments", ())
            ),
            git_nodes=tuple(
                GraphNode.from_dict(item) for item in payload.get("git_nodes", ())
            ),
            git_edges=tuple(
                GraphEdge.from_dict(item) for item in payload.get("git_edges", ())
            ),
            git_omitted=tuple(
                OmittedDiagnostic.from_dict(item)
                for item in payload.get("git_omitted", ())
            ),
            git_stats=dict(payload.get("git_stats", {}) or {}),
        )


__all__ = [
    "CACHE_SCHEMA_VERSION",
    "CacheFingerprint",
    "ExtractionCacheBundle",
    "FileIndexFragment",
]
