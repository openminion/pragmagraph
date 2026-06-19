"""Graphify-shaped JSON interop helpers for PragmaGraph snapshots."""

from __future__ import annotations

from typing import Any, Mapping

from pragmagraph.contracts import INDEXER_VERSION, SCHEMA_VERSION
from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef

GRAPHIFY_INTEROP_FORMAT = "pragmagraph.graphify.v1alpha1"
GRAPHIFY_INTEROP_SCHEMA_VERSION = "pragmagraph.graphify.schema.v1alpha1"


def _source_payload(source_ref: SourceRef) -> dict[str, Any]:
    return source_ref.to_dict()


def _node_payload(node: GraphNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.kind,
        "label": node.label,
        "properties": {
            "kind": node.kind,
            "text": node.text,
            "metadata": dict(node.metadata),
            "source_ref": _source_payload(node.source_ref),
        },
    }


def _edge_payload(edge: GraphEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "type": edge.kind,
        "source": edge.source_id,
        "target": edge.target_id,
        "properties": {
            "kind": edge.kind,
            "metadata": dict(edge.metadata),
            "source_ref": _source_payload(edge.source_ref),
        },
    }


def to_graphify_payload(snapshot: GraphSnapshot) -> dict[str, Any]:
    """Convert ``snapshot`` into deterministic Graphify-shaped JSON."""
    nodes = sorted(snapshot.nodes, key=lambda node: node.id)
    edges = sorted(snapshot.edges, key=lambda edge: edge.id)
    return {
        "format": GRAPHIFY_INTEROP_FORMAT,
        "interop_schema_version": GRAPHIFY_INTEROP_SCHEMA_VERSION,
        "source": {
            "schema_version": snapshot.schema_version,
            "indexer_version": snapshot.indexer_version,
            "namespace": snapshot.namespace,
            "root_path": snapshot.root_path,
            "created_at": snapshot.created_at,
        },
        "nodes": [_node_payload(node) for node in nodes],
        "edges": [_edge_payload(edge) for edge in edges],
        "omitted": [item.to_dict() for item in snapshot.omitted],
        "stats": dict(snapshot.stats),
    }


def _properties(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("properties", {})
    if isinstance(value, Mapping):
        return value
    return {}


def _source_ref_from_payload(payload: Mapping[str, Any]) -> SourceRef:
    properties = _properties(payload)
    source = properties.get("source_ref", {})
    if isinstance(source, Mapping):
        return SourceRef.from_dict(source)
    return SourceRef()


def snapshot_from_graphify_payload(
    payload: Mapping[str, Any],
    *,
    namespace: str = "graphify",
    root_path: str = "",
) -> GraphSnapshot:
    """Build a PragmaGraph snapshot from the supported Graphify-shaped subset."""
    source = payload.get("source", {})
    if isinstance(source, Mapping):
        namespace = str(source.get("namespace", "") or namespace)
        root_path = str(source.get("root_path", "") or root_path)
        created_at = str(source.get("created_at", "") or "")
        schema_version = str(source.get("schema_version", "") or SCHEMA_VERSION)
        indexer_version = str(source.get("indexer_version", "") or INDEXER_VERSION)
    else:
        created_at = ""
        schema_version = SCHEMA_VERSION
        indexer_version = INDEXER_VERSION

    nodes = []
    for item in payload.get("nodes", ()):
        if not isinstance(item, Mapping):
            continue
        properties = _properties(item)
        metadata = properties.get("metadata", {})
        nodes.append(
            GraphNode(
                id=str(item.get("id", "") or ""),
                kind=str(item.get("type", "") or properties.get("kind", "") or ""),
                label=str(item.get("label", "") or item.get("id", "") or ""),
                text=str(properties.get("text", "") or ""),
                source_ref=_source_ref_from_payload(item),
                metadata=dict(metadata) if isinstance(metadata, Mapping) else {},
            )
        )

    edges = []
    for item in payload.get("edges", ()):
        if not isinstance(item, Mapping):
            continue
        properties = _properties(item)
        metadata = properties.get("metadata", {})
        edges.append(
            GraphEdge(
                id=str(item.get("id", "") or ""),
                kind=str(item.get("type", "") or properties.get("kind", "") or ""),
                source_id=str(item.get("source", "") or ""),
                target_id=str(item.get("target", "") or ""),
                source_ref=_source_ref_from_payload(item),
                metadata=dict(metadata) if isinstance(metadata, Mapping) else {},
            )
        )

    return GraphSnapshot(
        namespace=namespace,
        root_path=root_path,
        nodes=tuple(node for node in nodes if node.id),
        edges=tuple(
            edge for edge in edges if edge.id and edge.source_id and edge.target_id
        ),
        stats=dict(payload.get("stats", {}) or {}),
        schema_version=schema_version,
        indexer_version=indexer_version,
        created_at=created_at,
    )


__all__ = [
    "GRAPHIFY_INTEROP_FORMAT",
    "GRAPHIFY_INTEROP_SCHEMA_VERSION",
    "snapshot_from_graphify_payload",
    "to_graphify_payload",
]
