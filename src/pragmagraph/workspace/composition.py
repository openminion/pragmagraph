"""Deterministic composition and exact cross-repository SCIP resolution."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from pragmagraph.contracts import (
    CROSS_REPO_RESOLUTION_SCHEMA_VERSION,
    EDGE_CONTAINS,
    EDGE_RESOLVES_TO,
    INDEXER_VERSION,
    NODE_PROJECT,
    NODE_WORKSPACE,
    RESOLUTION_KIND_EXACT_SCIP_SYMBOL,
    SCHEMA_VERSION,
)
from pragmagraph.interchange.scip_symbols import (
    ScipSymbolIdentity,
    require_cross_repository_symbol,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OmittedDiagnostic,
    PragmaGraphError,
    SourceRef,
)
from pragmagraph.portability import edge_id, node_id
from pragmagraph.storage import stable_dumps

DETAIL_SAMPLE_LIMIT = 100
AMBIGUITY_CANDIDATE_LIMIT = 20

OUTCOME_EXACT = "cross_repo_definition_exact"
OUTCOME_MISSING = "cross_repo_definition_missing"
OUTCOME_AMBIGUOUS = "cross_repo_definition_ambiguous"
OUTCOME_VERSION_MISMATCH = "cross_repo_package_version_mismatch"
OUTCOME_INVALID = "cross_repo_identity_invalid"
OUTCOME_SAME_ROOT = "cross_repo_definition_same_root"
RESOLUTION_OUTCOMES = (
    OUTCOME_EXACT,
    OUTCOME_MISSING,
    OUTCOME_AMBIGUOUS,
    OUTCOME_VERSION_MISMATCH,
    OUTCOME_INVALID,
    OUTCOME_SAME_ROOT,
)


@dataclass(frozen=True)
class NamedSnapshot:
    """One caller-named canonical snapshot input."""

    name: str
    snapshot: GraphSnapshot

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise PragmaGraphError(
                "snapshot input name is required",
                code="INVALID_SNAPSHOT_INPUT",
            )
        object.__setattr__(self, "name", name)


@dataclass(frozen=True)
class CrossRepoResolutionReport:
    """Complete outcome counts plus bounded diagnostic-detail counts."""

    outcome_counts: Mapping[str, int] = field(default_factory=dict)
    omitted_detail_counts: Mapping[str, int] = field(default_factory=dict)
    root_count: int = 0
    package_count: int = 0
    detail_sample_limit: int = DETAIL_SAMPLE_LIMIT
    ambiguity_candidate_limit: int = AMBIGUITY_CANDIDATE_LIMIT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "outcome_counts",
            MappingProxyType(
                {
                    name: int(self.outcome_counts.get(name, 0))
                    for name in RESOLUTION_OUTCOMES
                }
            ),
        )
        object.__setattr__(
            self,
            "omitted_detail_counts",
            MappingProxyType(
                {
                    name: int(self.omitted_detail_counts.get(name, 0))
                    for name in RESOLUTION_OUTCOMES
                }
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CROSS_REPO_RESOLUTION_SCHEMA_VERSION,
            "outcome_counts": dict(self.outcome_counts),
            "omitted_detail_counts": dict(self.omitted_detail_counts),
            "root_count": self.root_count,
            "package_count": self.package_count,
            "detail_sample_limit": self.detail_sample_limit,
            "ambiguity_candidate_limit": self.ambiguity_candidate_limit,
        }


@dataclass(frozen=True)
class SnapshotCompositionResult:
    """One composed canonical snapshot and its exact resolution report."""

    snapshot: GraphSnapshot
    report: CrossRepoResolutionReport


def compose_snapshots(
    inputs: Iterable[NamedSnapshot],
    *,
    namespace: str = "workspace",
    created_at: str = "",
) -> SnapshotCompositionResult:
    """Compose canonical snapshots and add exact cross-root resolution edges."""
    ordered = tuple(sorted(inputs, key=lambda item: item.name))
    _validate_inputs(ordered)
    workspace_id = node_id(namespace, NODE_WORKSPACE, ".")
    nodes: dict[str, GraphNode] = {
        workspace_id: GraphNode(
            id=workspace_id,
            kind=NODE_WORKSPACE,
            label=namespace,
            source_ref=SourceRef(path="."),
            metadata={"root_names": [item.name for item in ordered]},
        )
    }
    edges: dict[str, GraphEdge] = {}
    omitted: list[OmittedDiagnostic] = []
    manifests = [
        _merge_snapshot_input(
            item,
            namespace=namespace,
            workspace_id=workspace_id,
            nodes=nodes,
            edges=edges,
            omitted=omitted,
        )
        for item in ordered
    ]

    resolution_edges, diagnostics, report = _resolve_cross_repository(
        tuple(nodes.values()), namespace=namespace, root_count=len(ordered)
    )
    for edge in resolution_edges:
        _insert_unique(edges, edge.id, edge, "edge")
    omitted.extend(diagnostics)
    _validate_references(tuple(nodes.values()), tuple(edges.values()))
    snapshot = GraphSnapshot(
        namespace=namespace,
        root_path="",
        nodes=tuple(sorted(nodes.values(), key=lambda item: item.id)),
        edges=tuple(sorted(edges.values(), key=lambda item: item.id)),
        omitted=tuple(sorted(omitted, key=lambda item: (item.reason, item.item_id))),
        stats={
            "cross_repo_resolution_schema_version": (
                CROSS_REPO_RESOLUTION_SCHEMA_VERSION
            ),
            "workspace_roots": manifests,
            "cross_repo_resolution": report.to_dict(),
            "root_count": len(ordered),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "omitted_count": len(omitted),
        },
        schema_version=SCHEMA_VERSION,
        indexer_version=INDEXER_VERSION,
        created_at=created_at,
    )
    return SnapshotCompositionResult(snapshot=snapshot, report=report)


def _merge_snapshot_input(
    item: NamedSnapshot,
    *,
    namespace: str,
    workspace_id: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> dict[str, str]:
    snapshot = item.snapshot
    for node in snapshot.nodes:
        _insert_unique(
            nodes,
            node.id,
            replace(
                node,
                metadata={**dict(node.metadata), "workspace_root": item.name},
            ),
            "node",
        )
    for edge in snapshot.edges:
        _insert_unique(
            edges,
            edge.id,
            replace(
                edge,
                metadata={**dict(edge.metadata), "workspace_root": item.name},
            ),
            "edge",
        )
    omitted.extend(
        replace(
            diagnostic,
            details={**dict(diagnostic.details), "workspace_root": item.name},
        )
        for diagnostic in snapshot.omitted
    )
    project = next(node for node in snapshot.nodes if node.kind == NODE_PROJECT)
    contains_id = edge_id(namespace, workspace_id, EDGE_CONTAINS, project.id)
    _insert_unique(
        edges,
        contains_id,
        GraphEdge(
            id=contains_id,
            kind=EDGE_CONTAINS,
            source_id=workspace_id,
            target_id=project.id,
            source_ref=SourceRef(path=item.name),
            metadata={
                "workspace_root": item.name,
                "root_namespace": snapshot.namespace,
            },
        ),
        "edge",
    )
    return _root_manifest(item)


def save_composed_snapshot_atomic(snapshot: GraphSnapshot, path: str | Path) -> Path:
    """Atomically replace ``path`` with a deterministic composed snapshot."""
    payload = stable_dumps(snapshot)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return target


def _validate_inputs(inputs: tuple[NamedSnapshot, ...]) -> None:
    if not inputs:
        raise PragmaGraphError(
            "at least one snapshot input is required",
            code="NO_SNAPSHOT_INPUTS",
        )
    names = [item.name for item in inputs]
    namespaces = [item.snapshot.namespace for item in inputs]
    if len(names) != len(set(names)):
        raise PragmaGraphError(
            "snapshot input names must be unique",
            code="DUPLICATE_SNAPSHOT_INPUT",
        )
    if len(namespaces) != len(set(namespaces)):
        raise PragmaGraphError(
            "snapshot input namespaces must be unique",
            code="DUPLICATE_SNAPSHOT_NAMESPACE",
        )
    for item in inputs:
        snapshot = item.snapshot
        if snapshot.schema_version != SCHEMA_VERSION:
            raise PragmaGraphError(
                "snapshot schema versions must match the current contract",
                code="UNSUPPORTED_SCHEMA_VERSION",
                details={"input": item.name, "actual": snapshot.schema_version},
            )
        if (
            "multi_root_schema_version" in snapshot.stats
            or "cross_repo_resolution_schema_version" in snapshot.stats
            or any(node.kind == NODE_WORKSPACE for node in snapshot.nodes)
        ):
            raise PragmaGraphError(
                "nested snapshot composition is not supported",
                code="NESTED_SNAPSHOT_COMPOSITION",
                details={"input": item.name},
            )
        projects = [node for node in snapshot.nodes if node.kind == NODE_PROJECT]
        if len(projects) != 1:
            raise PragmaGraphError(
                "each snapshot must contain exactly one project node",
                code="INVALID_PROJECT_NODE_COUNT",
                details={"input": item.name, "count": len(projects)},
            )
        _validate_references(snapshot.nodes, snapshot.edges, input_name=item.name)


def _validate_references(
    nodes: Iterable[GraphNode],
    edges: Iterable[GraphEdge],
    *,
    input_name: str = "",
) -> None:
    node_ids = {node.id for node in nodes}
    for edge in edges:
        missing = [
            value for value in (edge.source_id, edge.target_id) if value not in node_ids
        ]
        if missing:
            raise PragmaGraphError(
                "snapshot edge references a missing node",
                code="SNAPSHOT_REFERENTIAL_GAP",
                details={"input": input_name, "edge_id": edge.id, "missing": missing},
            )


def _insert_unique(target: dict[str, Any], key: str, value: Any, kind: str) -> None:
    if key in target:
        raise PragmaGraphError(
            f"duplicate {kind} ID across snapshot inputs",
            code=f"DUPLICATE_{kind.upper()}_ID",
            details={"id": key},
        )
    target[key] = value


def _root_manifest(item: NamedSnapshot) -> dict[str, str]:
    snapshot = item.snapshot
    digest = hashlib.sha256(stable_dumps(snapshot).encode("utf-8")).hexdigest()
    return {
        "name": item.name,
        "namespace": snapshot.namespace,
        "schema_version": snapshot.schema_version,
        "indexer_version": snapshot.indexer_version,
        "created_at": snapshot.created_at,
        "sha256": digest,
    }


@dataclass(frozen=True)
class _ResolutionIndex:
    definitions: Mapping[str, tuple[GraphNode, ...]]
    definitions_by_versionless_key: Mapping[
        tuple[str, str, str, tuple[str, ...]], tuple[GraphNode, ...]
    ]
    identities: Mapping[str, ScipSymbolIdentity]
    package_count: int


def _resolve_cross_repository(
    nodes: tuple[GraphNode, ...],
    *,
    namespace: str,
    root_count: int,
) -> tuple[
    tuple[GraphEdge, ...], tuple[OmittedDiagnostic, ...], CrossRepoResolutionReport
]:
    index = _build_resolution_index(nodes)
    counts: Counter[str] = Counter()
    details: dict[str, list[OmittedDiagnostic]] = defaultdict(list)
    edges: list[GraphEdge] = []
    for node in sorted(nodes, key=lambda item: item.id):
        if node.metadata.get("scip_external") is not True:
            continue
        outcome, edge, extra = _resolve_external_node(
            node,
            index=index,
            namespace=namespace,
        )
        if edge is not None:
            edges.append(edge)
            counts[outcome] += 1
        else:
            _record_outcome(counts, details, outcome, node, extra)

    samples, omitted_detail_counts = _bounded_details(details)
    report = CrossRepoResolutionReport(
        outcome_counts=counts,
        omitted_detail_counts=omitted_detail_counts,
        root_count=root_count,
        package_count=index.package_count,
    )
    return tuple(sorted(edges, key=lambda item: item.id)), samples, report


def _build_resolution_index(nodes: tuple[GraphNode, ...]) -> _ResolutionIndex:
    definitions: dict[str, list[GraphNode]] = defaultdict(list)
    definitions_by_versionless_key: dict[
        tuple[str, str, str, tuple[str, ...]], list[GraphNode]
    ] = defaultdict(list)
    identities: dict[str, ScipSymbolIdentity] = {}
    packages: set[tuple[str, str, str]] = set()
    for node in sorted(nodes, key=lambda item: item.id):
        symbol = str(node.metadata.get("scip_symbol", "") or "")
        if not symbol:
            continue
        try:
            identity = require_cross_repository_symbol(symbol)
        except PragmaGraphError:
            continue
        identities[node.id] = identity
        packages.add(
            (
                identity.package_manager,
                identity.package_name,
                identity.package_version,
            )
        )
        if _is_definition(node):
            definitions[identity.original].append(node)
            definitions_by_versionless_key[identity.version_agnostic_key].append(node)
    return _ResolutionIndex(
        definitions={
            key: tuple(sorted(value, key=lambda item: item.id))
            for key, value in definitions.items()
        },
        definitions_by_versionless_key={
            key: tuple(sorted(value, key=lambda item: item.id))
            for key, value in definitions_by_versionless_key.items()
        },
        identities=identities,
        package_count=len(packages),
    )


def _resolve_external_node(
    node: GraphNode,
    *,
    index: _ResolutionIndex,
    namespace: str,
) -> tuple[str, GraphEdge | None, Mapping[str, Any]]:
    symbol = str(node.metadata.get("scip_symbol", "") or "")
    try:
        identity = require_cross_repository_symbol(symbol)
    except PragmaGraphError as exc:
        return OUTCOME_INVALID, None, {"error": exc.message}
    source_root = str(node.metadata.get("workspace_root", "") or "")
    exact = tuple(
        candidate
        for candidate in index.definitions.get(identity.original, ())
        if candidate.metadata.get("workspace_root") != source_root
    )
    if len(exact) == 1:
        return (
            OUTCOME_EXACT,
            _resolution_edge(node, exact[0], identity, namespace),
            {},
        )
    if len(exact) > 1:
        candidate_ids = [candidate.id for candidate in exact]
        return (
            OUTCOME_AMBIGUOUS,
            None,
            {
                "candidate_ids": candidate_ids[:AMBIGUITY_CANDIDATE_LIMIT],
                "omitted_candidate_count": max(
                    0, len(candidate_ids) - AMBIGUITY_CANDIDATE_LIMIT
                ),
            },
        )
    if any(
        candidate.metadata.get("workspace_root") == source_root
        for candidate in index.definitions.get(identity.original, ())
    ):
        return OUTCOME_SAME_ROOT, None, {}
    other_versions = tuple(
        candidate
        for candidate in index.definitions_by_versionless_key.get(
            identity.version_agnostic_key, ()
        )
        if candidate.metadata.get("workspace_root") != source_root
    )
    if other_versions:
        versions = sorted(
            {
                index.identities[candidate.id].package_version
                for candidate in other_versions
                if candidate.id in index.identities
            }
        )
        return OUTCOME_VERSION_MISMATCH, None, {"available_versions": versions}
    return OUTCOME_MISSING, None, {}


def _bounded_details(
    details: Mapping[str, list[OmittedDiagnostic]],
) -> tuple[tuple[OmittedDiagnostic, ...], dict[str, int]]:
    samples: list[OmittedDiagnostic] = []
    omitted_detail_counts: dict[str, int] = {}
    for outcome in RESOLUTION_OUTCOMES:
        records = sorted(details.get(outcome, ()), key=lambda item: item.item_id)
        samples.extend(records[:DETAIL_SAMPLE_LIMIT])
        omitted_detail_counts[outcome] = max(0, len(records) - DETAIL_SAMPLE_LIMIT)
    return tuple(samples), omitted_detail_counts


def _is_definition(node: GraphNode) -> bool:
    return (
        node.metadata.get("scip_external") is False
        and bool(node.source_ref.path)
        and node.source_ref.line is not None
    )


def _record_outcome(
    counts: Counter[str],
    details: dict[str, list[OmittedDiagnostic]],
    outcome: str,
    node: GraphNode,
    extra: Mapping[str, Any],
) -> None:
    counts[outcome] += 1
    details[outcome].append(
        OmittedDiagnostic(
            reason=outcome,
            item_id=node.id,
            details={
                "workspace_root": node.metadata.get("workspace_root", ""),
                **dict(extra),
            },
        )
    )


def _resolution_edge(
    source: GraphNode,
    target: GraphNode,
    identity: ScipSymbolIdentity,
    namespace: str,
) -> GraphEdge:
    source_root = str(source.metadata.get("workspace_root", "") or "")
    target_root = str(target.metadata.get("workspace_root", "") or "")
    metadata = {
        "resolution_kind": RESOLUTION_KIND_EXACT_SCIP_SYMBOL,
        "scip_symbol_sha256": hashlib.sha256(
            identity.original.encode("utf-8")
        ).hexdigest(),
        "consumer_workspace_root": source_root,
        "provider_workspace_root": target_root,
        "scip_package_manager": identity.package_manager,
        "scip_package_name": identity.package_name,
        "scip_package_version": identity.package_version,
    }
    for side, node in (("consumer", source), ("provider", target)):
        for key in ("producer", "scip_producer", "scip_producer_version"):
            value = node.metadata.get(key)
            if value not in (None, ""):
                metadata[f"{side}_{key}"] = value
    return GraphEdge(
        id=edge_id(namespace, source.id, EDGE_RESOLVES_TO, target.id),
        kind=EDGE_RESOLVES_TO,
        source_id=source.id,
        target_id=target.id,
        source_ref=source.source_ref,
        metadata=metadata,
    )


__all__ = [
    "AMBIGUITY_CANDIDATE_LIMIT",
    "CrossRepoResolutionReport",
    "DETAIL_SAMPLE_LIMIT",
    "NamedSnapshot",
    "SnapshotCompositionResult",
    "compose_snapshots",
    "save_composed_snapshot_atomic",
]
