"""Deterministic composition of explicitly named source roots."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from pragmagraph.adapters import index_path
from pragmagraph.contracts import EDGE_CONTAINS, NODE_PROJECT, NODE_WORKSPACE
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OmittedDiagnostic,
    PragmaGraphError,
    SourceRef,
)
from pragmagraph.portability import edge_id, node_id

MULTI_ROOT_SCHEMA_VERSION = "pragmagraph.multi_root.v1alpha1"


@dataclass(frozen=True)
class WorkspaceRoot:
    """One explicitly named root in a composed workspace."""

    name: str
    path: str
    namespace: str = ""

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise PragmaGraphError(
                "workspace root name is required", code="INVALID_ROOT"
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "path", str(Path(self.path).resolve()))
        object.__setattr__(self, "namespace", str(self.namespace or name))


def index_multi_root(
    roots: Iterable[WorkspaceRoot],
    *,
    namespace: str = "workspace",
    created_at: str = "",
) -> GraphSnapshot:
    """Index and compose roots while preserving root-scoped provenance."""
    ordered = tuple(sorted(roots, key=lambda item: (item.name, item.namespace)))
    _validate_roots(ordered)
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
    for root in ordered:
        snapshot = index_path(
            root.path, namespace=root.namespace, created_at=created_at
        )
        _merge_root(root, snapshot, workspace_id, namespace, nodes, edges, omitted)
    return GraphSnapshot(
        namespace=namespace,
        root_path="",
        nodes=tuple(sorted(nodes.values(), key=lambda item: item.id)),
        edges=tuple(sorted(edges.values(), key=lambda item: item.id)),
        omitted=tuple(sorted(omitted, key=lambda item: (item.reason, item.item_id))),
        stats={
            "multi_root_schema_version": MULTI_ROOT_SCHEMA_VERSION,
            "root_count": len(ordered),
            "root_names": tuple(item.name for item in ordered),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "omitted_count": len(omitted),
        },
        created_at=created_at,
    )


def _validate_roots(roots: tuple[WorkspaceRoot, ...]) -> None:
    names = [item.name for item in roots]
    namespaces = [item.namespace for item in roots]
    if not roots:
        raise PragmaGraphError(
            "at least one workspace root is required", code="NO_ROOTS"
        )
    if len(names) != len(set(names)):
        raise PragmaGraphError(
            "workspace root names must be unique", code="DUPLICATE_ROOT"
        )
    if len(namespaces) != len(set(namespaces)):
        raise PragmaGraphError(
            "workspace root namespaces must be unique",
            code="DUPLICATE_ROOT_NAMESPACE",
        )


def _merge_root(
    root: WorkspaceRoot,
    snapshot: GraphSnapshot,
    workspace_id: str,
    workspace_namespace: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    for item in snapshot.nodes:
        nodes[item.id] = replace(
            item,
            metadata={**dict(item.metadata), "workspace_root": root.name},
        )
    for item in snapshot.edges:
        edges[item.id] = replace(
            item,
            metadata={**dict(item.metadata), "workspace_root": root.name},
        )
    omitted.extend(
        replace(item, details={**dict(item.details), "workspace_root": root.name})
        for item in snapshot.omitted
    )
    project = next((item for item in snapshot.nodes if item.kind == NODE_PROJECT), None)
    if project is None:
        return
    link_id = edge_id(workspace_namespace, workspace_id, EDGE_CONTAINS, project.id)
    edges[link_id] = GraphEdge(
        id=link_id,
        kind=EDGE_CONTAINS,
        source_id=workspace_id,
        target_id=project.id,
        source_ref=SourceRef(path=root.name),
        metadata={"workspace_root": root.name, "root_namespace": root.namespace},
    )


__all__ = ["MULTI_ROOT_SCHEMA_VERSION", "WorkspaceRoot", "index_multi_root"]
