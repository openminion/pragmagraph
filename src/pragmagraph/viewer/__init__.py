"""Provider-neutral viewer envelopes for scalable graph surfaces."""

from __future__ import annotations

from typing import Any, Mapping

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot
from pragmagraph.query import neighborhood, path
from pragmagraph.refresh import diff_snapshots
from pragmagraph.viewer.envelope import (
    DEFAULT_GENERATED_AT,
    VIEWER_ENVELOPE_SCHEMA_VERSION,
    VIEWER_FIXTURE_SCENARIOS,
    ViewerGraphEnvelope,
    color_hint,
    load_viewer_envelope,
    viewer_capabilities,
    viewer_compatibility,
    write_viewer_envelope,
)
from pragmagraph.viewer.fixtures import build_viewer_fixture_envelope


def build_viewer_envelope(
    snapshot: GraphSnapshot,
    *,
    level_of_detail: str = "auto",
    node_budget: int = 240,
    edge_budget: int = 480,
    cluster_size: int = 24,
) -> ViewerGraphEnvelope:
    """Build a deterministic viewer envelope from an observed snapshot."""

    raw_node_count = len(snapshot.nodes)
    raw_edge_count = len(snapshot.edges)
    lod = _resolve_lod(level_of_detail, raw_node_count)
    clusters = _clusters_from_snapshot(snapshot, cluster_size=max(4, cluster_size))
    selected_nodes = _selected_nodes(snapshot.nodes, clusters, lod, node_budget)
    selected_node_ids = {node.id for node in selected_nodes}
    selected_edges = tuple(
        edge
        for edge in snapshot.edges
        if edge.source_id in selected_node_ids and edge.target_id in selected_node_ids
    )[:edge_budget]
    omitted = _omitted_records(
        raw_node_count=raw_node_count,
        raw_edge_count=raw_edge_count,
        visible_node_count=len(selected_nodes),
        visible_edge_count=len(selected_edges),
    ) + tuple(item.to_dict() for item in snapshot.omitted)
    return ViewerGraphEnvelope(
        schema_version=VIEWER_ENVELOPE_SCHEMA_VERSION,
        producer={"package": "pragmagraph", "contract": "viewer-envelope"},
        snapshot_id=_snapshot_id(snapshot),
        snapshot_version=snapshot.indexer_version,
        root_identity={
            "namespace": snapshot.namespace,
            "root_path": snapshot.root_path,
        },
        generated_at=snapshot.created_at or DEFAULT_GENERATED_AT,
        graph_stats={
            "raw_node_count": raw_node_count,
            "raw_edge_count": raw_edge_count,
            "visible_node_count": len(selected_nodes),
            "visible_edge_count": len(selected_edges),
            "cluster_count": len(clusters),
        },
        render_hint={
            "preferred_engine": "3d" if raw_node_count >= 1000 else "canvas",
            "layout": "islands" if raw_node_count >= 1000 else "force",
            "theme": "space" if raw_node_count >= 1000 else "default",
        },
        level_of_detail=lod,
        nodes=tuple(_node_record(node, clusters) for node in selected_nodes),
        edges=tuple(_edge_record(edge) for edge in selected_edges),
        clusters=clusters,
        edge_bundles=_edge_bundles(snapshot.edges, clusters),
        omitted=omitted,
        expansion=_expansion_records(clusters),
        content_index={
            node.id: _content_record(node, mode="preview") for node in selected_nodes
        },
        evidence_index={
            node.id: _evidence_record(node, snapshot.edges) for node in selected_nodes
        },
        provenance=tuple(_provenance_record(node) for node in selected_nodes),
        capabilities=viewer_capabilities(),
        compatibility=viewer_compatibility(),
    )


def viewer_cluster(
    envelope: ViewerGraphEnvelope, cluster_id: str, *, budget: int = 100
) -> dict[str, Any]:
    cluster = _find_cluster(envelope, cluster_id)
    candidate_ids = _cluster_node_ids(cluster)
    visible_nodes = _nodes_by_id(envelope)
    nodes = [
        visible_nodes[node_id] for node_id in candidate_ids if node_id in visible_nodes
    ]
    nodes = nodes[:budget]
    return {
        "cluster": cluster,
        "nodes": nodes,
        "representative_node_ids": list(cluster.get("representative_node_ids", ())),
        "hub_node_ids": list(cluster.get("hub_node_ids", ())),
        "bridge_node_ids": list(cluster.get("bridge_node_ids", ())),
        "omitted": _omitted_detail(
            reason="cluster_budget",
            raw_count=int(cluster.get("node_count", 0)),
            visible_count=len(nodes),
        ),
        "budget": budget,
        "cursor": cluster.get("expansion_cursor", ""),
    }


def viewer_content(
    envelope: ViewerGraphEnvelope,
    node_id: str,
    *,
    mode: str = "preview",
) -> dict[str, Any]:
    content = dict(envelope.content_index.get(node_id) or {})
    if not content:
        raise KeyError(f"viewer content node id not found: {node_id}")
    content["mode"] = mode
    if mode == "full":
        content["text"] = (
            f"{content.get('text', '')}\n\nFull content is provider-owned and retrieved through this explicit lookup."
        )
    return {"node_id": node_id, "content": content}


def viewer_neighborhood(
    snapshot: GraphSnapshot,
    node_id: str,
    *,
    depth: int = 1,
    budget: int = 100,
) -> dict[str, Any]:
    result = neighborhood(snapshot, node_id, depth=depth, max_results=budget)
    return result.to_dict()


def viewer_envelope_neighborhood(
    envelope: ViewerGraphEnvelope,
    node_id: str,
    *,
    depth: int = 1,
    budget: int = 100,
) -> dict[str, Any]:
    _require_envelope_node(envelope, node_id)
    node_map = _nodes_by_id(envelope)
    edge_map = _edges_by_id(envelope)
    visited = {node_id}
    frontier = [(node_id, 0)]
    found_ids: list[str] = []
    found_edge_ids: list[str] = []
    while frontier:
        current, current_depth = frontier.pop(0)
        if current_depth >= depth:
            continue
        for edge in _incident_viewer_edges(envelope, current):
            edge_id = str(edge["id"])
            other = _other_viewer_node(edge, current)
            if other in visited:
                continue
            visited.add(other)
            found_edge_ids.append(edge_id)
            if other in node_map:
                found_ids.append(other)
                frontier.append((other, current_depth + 1))
    bounded_node_ids = found_ids[:budget]
    bounded_edge_ids = found_edge_ids[:budget]
    return {
        "node_id": node_id,
        "depth": depth,
        "budget": budget,
        "nodes": [node_map[node_id] for node_id in bounded_node_ids],
        "edges": [
            edge_map[edge_id] for edge_id in bounded_edge_ids if edge_id in edge_map
        ],
        "omitted": _omitted_detail(
            reason="neighborhood_budget",
            raw_count=len(found_ids),
            visible_count=len(bounded_node_ids),
        ),
        "cursor": _cursor("neighborhood", node_id, len(bounded_node_ids)),
    }


def viewer_path(
    snapshot: GraphSnapshot,
    source_id: str,
    target_id: str,
    *,
    budget: int = 100,
) -> dict[str, Any]:
    result = path(snapshot, source_id, target_id, max_hops=max(1, budget))
    return result.to_dict()


def viewer_envelope_path(
    envelope: ViewerGraphEnvelope,
    source_id: str,
    target_id: str,
    *,
    budget: int = 100,
) -> dict[str, Any]:
    _require_envelope_node(envelope, source_id)
    _require_envelope_node(envelope, target_id)
    node_map = _nodes_by_id(envelope)
    edge_map = _edges_by_id(envelope)
    queue: list[tuple[str, list[str], list[str]]] = [(source_id, [source_id], [])]
    visited = {source_id}
    while queue:
        current, node_path, edge_path = queue.pop(0)
        if current == target_id:
            bounded_nodes = node_path[:budget]
            bounded_edges = edge_path[: max(0, budget - 1)]
            return {
                "source_id": source_id,
                "target_id": target_id,
                "found": True,
                "budget": budget,
                "nodes": [node_map[node_id] for node_id in bounded_nodes],
                "edges": [
                    edge_map[edge_id]
                    for edge_id in bounded_edges
                    if edge_id in edge_map
                ],
                "omitted": _omitted_detail(
                    reason="path_budget",
                    raw_count=len(node_path),
                    visible_count=len(bounded_nodes),
                ),
            }
        if len(edge_path) >= budget:
            continue
        for edge in _incident_viewer_edges(envelope, current):
            other = _other_viewer_node(edge, current)
            if other in visited or other not in node_map:
                continue
            visited.add(other)
            queue.append((other, [*node_path, other], [*edge_path, str(edge["id"])]))
    return {
        "source_id": source_id,
        "target_id": target_id,
        "found": False,
        "budget": budget,
        "nodes": [],
        "edges": [],
        "omitted": (),
    }


def viewer_cluster_nodes(
    envelope: ViewerGraphEnvelope,
    cluster_id: str,
    *,
    role: str,
    budget: int = 100,
) -> dict[str, Any]:
    cluster = _find_cluster(envelope, cluster_id)
    if role not in {"hub", "bridge"}:
        raise ValueError("viewer cluster node role must be 'hub' or 'bridge'")
    key = "hub_node_ids" if role == "hub" else "bridge_node_ids"
    node_ids = [str(node_id) for node_id in cluster.get(key, ())]
    visible_nodes = _nodes_by_id(envelope)
    bounded_ids = node_ids[:budget]
    return {
        "cluster_id": cluster_id,
        "role": role,
        "budget": budget,
        "node_ids": bounded_ids,
        "nodes": [
            visible_nodes[node_id]
            for node_id in bounded_ids
            if node_id in visible_nodes
        ],
        "omitted": _omitted_detail(
            reason=f"{role}_node_budget",
            raw_count=len(node_ids),
            visible_count=len(bounded_ids),
        ),
        "cursor": _cursor(f"{role}-nodes", cluster_id, len(bounded_ids)),
    }


def viewer_delta(
    before: GraphSnapshot,
    after: GraphSnapshot,
    *,
    budget: int = 100,
) -> dict[str, Any]:
    delta = diff_snapshots(before, after)
    markers = (
        _delta_markers("added", "node", delta.added_node_ids)
        + _delta_markers("removed", "node", delta.removed_node_ids)
        + _delta_markers("added", "edge", delta.added_edge_ids)
        + _delta_markers("removed", "edge", delta.removed_edge_ids)
        + _delta_markers("added", "omitted", delta.added_omitted_ids)
        + _delta_markers("removed", "omitted", delta.removed_omitted_ids)
    )
    bounded = markers[:budget]
    return {
        "before_snapshot_id": _snapshot_id(before),
        "after_snapshot_id": _snapshot_id(after),
        "budget": budget,
        "structural_delta": delta.to_dict(),
        "markers": bounded,
        "freshness": _freshness_summary(bounded),
        "omitted": _omitted_detail(
            reason="delta_budget",
            raw_count=len(markers),
            visible_count=len(bounded),
        ),
    }


def explain_omitted(
    envelope: ViewerGraphEnvelope,
    *,
    reason: str = "",
) -> dict[str, Any]:
    omitted = [dict(item) for item in envelope.omitted]
    if reason:
        omitted = [item for item in omitted if item.get("reason") == reason]
    return {
        "snapshot_id": envelope.snapshot_id,
        "reason": reason,
        "omitted": omitted,
    }


def _resolve_lod(level_of_detail: str, raw_node_count: int) -> str:
    if level_of_detail != "auto":
        return level_of_detail
    if raw_node_count >= 1_000_000:
        return "meta"
    if raw_node_count >= 50_000:
        return "cluster"
    if raw_node_count >= 2_000:
        return "sampled"
    return "raw"


def _snapshot_id(snapshot: GraphSnapshot) -> str:
    return f"{snapshot.namespace}:{snapshot.created_at or snapshot.root_path or 'snapshot'}"


def _clusters_from_snapshot(
    snapshot: GraphSnapshot,
    *,
    cluster_size: int,
) -> tuple[Mapping[str, Any], ...]:
    node_ids = sorted(node.id for node in snapshot.nodes)
    edge_counts = _edge_counts_by_node(snapshot.edges)
    clusters: list[Mapping[str, Any]] = []
    for index in range(0, len(node_ids), cluster_size):
        members = node_ids[index : index + cluster_size]
        cluster_number = index // cluster_size + 1
        cluster_id = f"cluster:{cluster_number:03d}"
        hubs = tuple(
            sorted(
                members, key=lambda node_id: (-edge_counts.get(node_id, 0), node_id)
            )[:3]
        )
        clusters.append(
            {
                "id": cluster_id,
                "label": f"Observed Cluster {cluster_number:02d}",
                "kind": "structural",
                "node_count": len(members),
                "edge_count": sum(edge_counts.get(node_id, 0) for node_id in members),
                "internal_edge_count": 0,
                "external_edge_count": 0,
                "representative_node_ids": members[:5],
                "hub_node_ids": hubs,
                "bridge_node_ids": hubs[:2],
                "warning_count": 0,
                "source_kinds": tuple(
                    sorted(
                        {
                            node.kind
                            for node in snapshot.nodes
                            if node.id in set(members)
                        }
                    )
                ),
                "centroid_hint": {
                    "x": (cluster_number % 12) / 12,
                    "y": cluster_number // 12,
                },
                "color_hint": color_hint(cluster_number),
                "freshness": "observed",
                "omitted": max(0, len(members) - 5),
                "expansion_cursor": f"cluster:{cluster_id}:offset:0",
            }
        )
    return tuple(clusters)


def _selected_nodes(
    nodes: tuple[GraphNode, ...],
    clusters: tuple[Mapping[str, Any], ...],
    lod: str,
    node_budget: int,
) -> tuple[GraphNode, ...]:
    if lod == "raw":
        return tuple(sorted(nodes, key=lambda node: node.id)[:node_budget])
    representative_ids = {
        node_id
        for cluster in clusters
        for node_id in cluster.get("representative_node_ids", ())
    }
    ranked = sorted(
        nodes,
        key=lambda node: (
            node.id not in representative_ids,
            node.kind,
            node.source_ref.path,
            node.id,
        ),
    )
    return tuple(ranked[:node_budget])


def _node_record(
    node: GraphNode,
    clusters: tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    cluster_id = _cluster_id_for_node(node.id, clusters)
    return {
        "id": node.id,
        "label": node.label,
        "kind": node.kind,
        "source_kind": node.source_ref.path.rsplit(".", 1)[-1]
        if node.source_ref.path
        else node.kind,
        "cluster_id": cluster_id,
        "summary": node.text or node.source_ref.path or node.label,
        "degree": 0,
        "confidence": node.metadata.get("confidence", 1.0),
        "freshness": node.metadata.get("freshness", "observed"),
        "evidence_count": 1 if node.source_ref.path else 0,
        "provenance_count": 1 if node.source_ref.path else 0,
        "include_reason": "representative" if cluster_id else "raw",
        "source_ref": node.source_ref.to_dict(),
    }


def _edge_record(edge: GraphEdge) -> Mapping[str, Any]:
    return {
        "id": edge.id,
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "kind": edge.kind,
        "confidence": edge.metadata.get("confidence", 1.0),
        "freshness": edge.metadata.get("freshness", "observed"),
        "source_ref": edge.source_ref.to_dict(),
    }


def _content_record(node: GraphNode, *, mode: str) -> Mapping[str, Any]:
    return {
        "mode": mode,
        "title": node.label,
        "text": node.text or node.source_ref.path or node.id,
        "source_ref": node.source_ref.to_dict(),
        "full_content_available": True,
    }


def _evidence_record(
    node: GraphNode,
    edges: tuple[GraphEdge, ...],
) -> Mapping[str, Any]:
    edge_count = sum(
        1 for edge in edges if edge.source_id == node.id or edge.target_id == node.id
    )
    return {"count": edge_count + (1 if node.source_ref.path else 0), "items": ()}


def _provenance_record(node: GraphNode) -> Mapping[str, Any]:
    return {
        "id": f"provenance:{node.id}",
        "node_id": node.id,
        "source": node.source_ref.path or node.kind,
        "observed_at": node.metadata.get("observed_at", ""),
    }


def _edge_counts_by_node(edges: tuple[GraphEdge, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for edge in edges:
        counts[edge.source_id] = counts.get(edge.source_id, 0) + 1
        counts[edge.target_id] = counts.get(edge.target_id, 0) + 1
    return counts


def _cluster_id_for_node(
    node_id: str,
    clusters: tuple[Mapping[str, Any], ...],
) -> str:
    for cluster in clusters:
        if node_id in set(cluster.get("representative_node_ids", ())):
            return str(cluster["id"])
    return ""


def _edge_bundles(
    edges: tuple[GraphEdge, ...],
    clusters: tuple[Mapping[str, Any], ...],
) -> tuple[Mapping[str, Any], ...]:
    node_to_cluster = {
        node_id: str(cluster["id"])
        for cluster in clusters
        for node_id in cluster.get("representative_node_ids", ())
    }
    bundles: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edges:
        source = node_to_cluster.get(edge.source_id)
        target = node_to_cluster.get(edge.target_id)
        if not source or not target or source == target:
            continue
        key = tuple(sorted((source, target)))
        bundle = bundles.setdefault(
            key,
            {
                "id": f"bundle:{key[0]}:{key[1]}",
                "source_cluster_id": key[0],
                "target_cluster_id": key[1],
                "edge_count": 0,
                "edge_kind_counts": {},
                "representative_edge_ids": [],
            },
        )
        bundle["edge_count"] += 1
        kind_counts = bundle["edge_kind_counts"]
        kind_counts[edge.kind] = kind_counts.get(edge.kind, 0) + 1
        if len(bundle["representative_edge_ids"]) < 3:
            bundle["representative_edge_ids"].append(edge.id)
    return tuple(
        dict(item) for item in sorted(bundles.values(), key=lambda item: item["id"])
    )


def _omitted_records(
    *,
    raw_node_count: int,
    raw_edge_count: int,
    visible_node_count: int,
    visible_edge_count: int,
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    if raw_node_count > visible_node_count:
        records.append(
            {
                "reason": "node_budget",
                "count": raw_node_count - visible_node_count,
                "details": {"visible": visible_node_count, "raw": raw_node_count},
            }
        )
    if raw_edge_count > visible_edge_count:
        records.append(
            {
                "reason": "edge_budget",
                "count": raw_edge_count - visible_edge_count,
                "details": {"visible": visible_edge_count, "raw": raw_edge_count},
            }
        )
    return tuple(records)


def _expansion_records(
    clusters: tuple[Mapping[str, Any], ...],
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        {
            "scope": "cluster",
            "cluster_id": cluster["id"],
            "cursor": cluster["expansion_cursor"],
            "default_budget": 100,
            "available_node_count": cluster["node_count"],
        }
        for cluster in clusters
    )


def _find_cluster(
    envelope: ViewerGraphEnvelope,
    cluster_id: str,
) -> Mapping[str, Any]:
    for cluster in envelope.clusters:
        if cluster.get("id") == cluster_id:
            return cluster
    raise KeyError(f"viewer cluster id not found: {cluster_id}")


def _cluster_node_ids(cluster: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("representative_node_ids", "hub_node_ids", "bridge_node_ids"):
        ids.extend(str(node_id) for node_id in cluster.get(key, ()))
    return list(dict.fromkeys(ids))


def _nodes_by_id(envelope: ViewerGraphEnvelope) -> dict[str, Mapping[str, Any]]:
    return {str(node["id"]): node for node in envelope.nodes}


def _edges_by_id(envelope: ViewerGraphEnvelope) -> dict[str, Mapping[str, Any]]:
    return {str(edge["id"]): edge for edge in envelope.edges}


def _require_envelope_node(
    envelope: ViewerGraphEnvelope,
    node_id: str,
) -> Mapping[str, Any]:
    node = _nodes_by_id(envelope).get(node_id)
    if node is None:
        raise KeyError(f"viewer node id not found: {node_id}")
    return node


def _incident_viewer_edges(
    envelope: ViewerGraphEnvelope,
    node_id: str,
) -> list[Mapping[str, Any]]:
    return [
        edge
        for edge in envelope.edges
        if edge.get("source_id") == node_id or edge.get("target_id") == node_id
    ]


def _other_viewer_node(edge: Mapping[str, Any], node_id: str) -> str:
    source_id = str(edge.get("source_id", ""))
    target_id = str(edge.get("target_id", ""))
    return target_id if source_id == node_id else source_id


def _omitted_detail(
    *,
    reason: str,
    raw_count: int,
    visible_count: int,
) -> tuple[Mapping[str, Any], ...]:
    if raw_count <= visible_count:
        return ()
    return (
        {
            "reason": reason,
            "count": raw_count - visible_count,
            "details": {"raw": raw_count, "visible": visible_count},
        },
    )


def _cursor(scope: str, item_id: str, offset: int) -> str:
    return f"{scope}:{item_id}:offset:{offset}"


def _delta_markers(
    status: str,
    item_kind: str,
    item_ids: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    return [
        {
            "id": f"delta:{status}:{item_kind}:{item_id}",
            "item_id": item_id,
            "item_kind": item_kind,
            "status": status,
            "freshness": "removed" if status == "removed" else "changed",
        }
        for item_id in item_ids
    ]


def _freshness_summary(markers: list[Mapping[str, Any]]) -> Mapping[str, int]:
    summary: dict[str, int] = {}
    for marker in markers:
        freshness = str(marker.get("freshness", "changed"))
        summary[freshness] = summary.get(freshness, 0) + 1
    return summary


__all__ = [
    "VIEWER_ENVELOPE_SCHEMA_VERSION",
    "VIEWER_FIXTURE_SCENARIOS",
    "ViewerGraphEnvelope",
    "build_viewer_envelope",
    "build_viewer_fixture_envelope",
    "explain_omitted",
    "load_viewer_envelope",
    "viewer_cluster",
    "viewer_cluster_nodes",
    "viewer_content",
    "viewer_delta",
    "viewer_envelope_neighborhood",
    "viewer_envelope_path",
    "viewer_neighborhood",
    "viewer_path",
    "write_viewer_envelope",
]
