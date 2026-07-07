"""Provider-neutral viewer envelopes for scalable graph surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import random
from typing import Any, Mapping

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot
from pragmagraph.query import neighborhood, path

VIEWER_ENVELOPE_SCHEMA_VERSION = "pragmagraph.viewer.v1alpha1"
VIEWER_FIXTURE_SCENARIOS = ("viewer-scale-1k", "viewer-scale-200k", "viewer-scale-1m")

_DEFAULT_GENERATED_AT = "2026-07-06T00:00:00+00:00"
_NODE_KINDS = (
    "file",
    "symbol",
    "document",
    "test",
    "memory",
    "task",
    "warning",
    "artifact",
)
_EDGE_KINDS = ("imports", "references", "documents", "tests", "mentions", "depends")


@dataclass(frozen=True)
class ViewerGraphEnvelope:
    """Stable JSON envelope consumed by provider-neutral graph viewers."""

    schema_version: str
    producer: Mapping[str, Any]
    snapshot_id: str
    snapshot_version: str
    root_identity: Mapping[str, Any]
    generated_at: str
    graph_stats: Mapping[str, Any]
    render_hint: Mapping[str, Any]
    level_of_detail: str
    nodes: tuple[Mapping[str, Any], ...] = ()
    edges: tuple[Mapping[str, Any], ...] = ()
    clusters: tuple[Mapping[str, Any], ...] = ()
    edge_bundles: tuple[Mapping[str, Any], ...] = ()
    omitted: tuple[Mapping[str, Any], ...] = ()
    expansion: tuple[Mapping[str, Any], ...] = ()
    content_index: Mapping[str, Any] = field(default_factory=dict)
    evidence_index: Mapping[str, Any] = field(default_factory=dict)
    provenance: tuple[Mapping[str, Any], ...] = ()
    capabilities: Mapping[str, Any] = field(default_factory=dict)
    compatibility: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "producer": dict(self.producer),
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "root_identity": dict(self.root_identity),
            "generated_at": self.generated_at,
            "graph_stats": dict(self.graph_stats),
            "render_hint": dict(self.render_hint),
            "level_of_detail": self.level_of_detail,
            "nodes": [dict(item) for item in self.nodes],
            "edges": [dict(item) for item in self.edges],
            "clusters": [dict(item) for item in self.clusters],
            "edge_bundles": [dict(item) for item in self.edge_bundles],
            "omitted": [dict(item) for item in self.omitted],
            "expansion": [dict(item) for item in self.expansion],
            "content_index": dict(self.content_index),
            "evidence_index": dict(self.evidence_index),
            "provenance": [dict(item) for item in self.provenance],
            "capabilities": dict(self.capabilities),
            "compatibility": dict(self.compatibility),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ViewerGraphEnvelope":
        return cls(
            schema_version=str(payload.get("schema_version") or ""),
            producer=dict(payload.get("producer") or {}),
            snapshot_id=str(payload.get("snapshot_id") or ""),
            snapshot_version=str(payload.get("snapshot_version") or ""),
            root_identity=dict(payload.get("root_identity") or {}),
            generated_at=str(payload.get("generated_at") or ""),
            graph_stats=dict(payload.get("graph_stats") or {}),
            render_hint=dict(payload.get("render_hint") or {}),
            level_of_detail=str(payload.get("level_of_detail") or "raw"),
            nodes=tuple(dict(item) for item in payload.get("nodes") or ()),
            edges=tuple(dict(item) for item in payload.get("edges") or ()),
            clusters=tuple(dict(item) for item in payload.get("clusters") or ()),
            edge_bundles=tuple(
                dict(item) for item in payload.get("edge_bundles") or ()
            ),
            omitted=tuple(dict(item) for item in payload.get("omitted") or ()),
            expansion=tuple(dict(item) for item in payload.get("expansion") or ()),
            content_index=dict(payload.get("content_index") or {}),
            evidence_index=dict(payload.get("evidence_index") or {}),
            provenance=tuple(dict(item) for item in payload.get("provenance") or ()),
            capabilities=dict(payload.get("capabilities") or {}),
            compatibility=dict(payload.get("compatibility") or {}),
        )


def load_viewer_envelope(path: str) -> ViewerGraphEnvelope:
    payload = json.loads(Path(path).expanduser().resolve(strict=True).read_text())
    return ViewerGraphEnvelope.from_dict(payload)


def write_viewer_envelope(envelope: ViewerGraphEnvelope, out: str) -> dict[str, Any]:
    path = Path(out).expanduser().resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(envelope.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "output_path": str(path),
        "schema_version": envelope.schema_version,
        "snapshot_id": envelope.snapshot_id,
        "level_of_detail": envelope.level_of_detail,
        "raw_node_count": envelope.graph_stats.get("raw_node_count", 0),
        "visible_node_count": len(envelope.nodes),
        "cluster_count": len(envelope.clusters),
    }


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
        generated_at=snapshot.created_at or _DEFAULT_GENERATED_AT,
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
        capabilities=_capabilities(),
        compatibility=_compatibility(),
    )


def build_viewer_fixture_envelope(
    scenario: str,
    *,
    node_budget: int = 240,
    edge_budget: int = 480,
    seed: int = 20260706,
) -> ViewerGraphEnvelope:
    if scenario not in VIEWER_FIXTURE_SCENARIOS:
        supported = ", ".join(VIEWER_FIXTURE_SCENARIOS)
        raise ValueError(
            f"unsupported viewer fixture scenario {scenario!r}; supported: {supported}"
        )
    raw_node_count = {
        "viewer-scale-1k": 1_000,
        "viewer-scale-200k": 200_000,
        "viewer-scale-1m": 1_000_000,
    }[scenario]
    raw_edge_count = int(raw_node_count * 1.45)
    rng = random.Random(f"{seed}:{scenario}")
    cluster_count = _fixture_cluster_count(raw_node_count)
    clusters = _fixture_clusters(
        rng, scenario, raw_node_count, raw_edge_count, cluster_count
    )
    visible_nodes = _fixture_nodes(rng, clusters, node_budget)
    visible_edges = _fixture_edges(rng, visible_nodes, clusters, edge_budget)
    omitted = _omitted_records(
        raw_node_count=raw_node_count,
        raw_edge_count=raw_edge_count,
        visible_node_count=len(visible_nodes),
        visible_edge_count=len(visible_edges),
    )
    return ViewerGraphEnvelope(
        schema_version=VIEWER_ENVELOPE_SCHEMA_VERSION,
        producer={
            "package": "pragmagraph",
            "contract": "viewer-envelope",
            "fixture_seed": seed,
        },
        snapshot_id=f"fixture:{scenario}:{seed}",
        snapshot_version="fixture.v1",
        root_identity={"namespace": scenario, "root_path": "synthetic-viewer-fixture"},
        generated_at=_DEFAULT_GENERATED_AT,
        graph_stats={
            "raw_node_count": raw_node_count,
            "raw_edge_count": raw_edge_count,
            "visible_node_count": len(visible_nodes),
            "visible_edge_count": len(visible_edges),
            "cluster_count": len(clusters),
            "minimum_raw_nodes_per_cluster": min(
                int(cluster["node_count"]) for cluster in clusters
            ),
        },
        render_hint={
            "preferred_engine": "3d",
            "layout": "islands",
            "theme": "space",
            "node_scale": 0.52,
            "label_mode": "progressive",
            "edge_mode": "bundled",
        },
        level_of_detail="cluster" if raw_node_count < 1_000_000 else "meta",
        nodes=visible_nodes,
        edges=visible_edges,
        clusters=clusters,
        edge_bundles=_fixture_edge_bundles(rng, clusters, edge_budget),
        omitted=omitted,
        expansion=_expansion_records(clusters),
        content_index={
            str(node["id"]): {
                "mode": "preview",
                "title": node["label"],
                "text": f"Synthetic observed content preview for {node['label']}.",
                "full_content_available": True,
            }
            for node in visible_nodes
        },
        evidence_index={
            str(node["id"]): {"count": int(node.get("evidence_count", 0)), "items": ()}
            for node in visible_nodes
        },
        provenance=tuple(
            {
                "id": f"provenance:{node['id']}",
                "node_id": node["id"],
                "source": node["source_kind"],
                "observed_at": _DEFAULT_GENERATED_AT,
            }
            for node in visible_nodes
        ),
        capabilities=_capabilities(),
        compatibility=_compatibility(),
    )


def viewer_cluster(
    envelope: ViewerGraphEnvelope, cluster_id: str, *, budget: int = 100
) -> dict[str, Any]:
    cluster = _find_cluster(envelope, cluster_id)
    nodes = [node for node in envelope.nodes if node.get("cluster_id") == cluster_id][
        :budget
    ]
    return {
        "cluster": cluster,
        "nodes": nodes,
        "omitted": max(0, int(cluster.get("node_count", 0)) - len(nodes)),
        "budget": budget,
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


def viewer_path(
    snapshot: GraphSnapshot,
    source_id: str,
    target_id: str,
    *,
    budget: int = 100,
) -> dict[str, Any]:
    result = path(snapshot, source_id, target_id, max_hops=max(1, budget))
    return result.to_dict()


def explain_omitted(envelope: ViewerGraphEnvelope) -> dict[str, Any]:
    return {
        "snapshot_id": envelope.snapshot_id,
        "omitted": [dict(item) for item in envelope.omitted],
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
                "color_hint": _color_hint(cluster_number),
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


def _fixture_cluster_count(raw_node_count: int) -> int:
    if raw_node_count <= 1_000:
        return 10
    if raw_node_count <= 200_000:
        return 96
    return 128


def _fixture_clusters(
    rng: random.Random,
    scenario: str,
    raw_node_count: int,
    raw_edge_count: int,
    cluster_count: int,
) -> tuple[Mapping[str, Any], ...]:
    node_counts = _fixture_cluster_node_counts(rng, raw_node_count, cluster_count)
    clusters: list[Mapping[str, Any]] = []
    for index in range(cluster_count):
        node_count = node_counts[index]
        edge_count = int(raw_edge_count * (node_count / raw_node_count))
        cluster_id = f"scale-{index + 1:03d}"
        kind = _NODE_KINDS[index % len(_NODE_KINDS)]
        clusters.append(
            {
                "id": cluster_id,
                "label": f"Scale {index + 1:03d}",
                "kind": kind,
                "node_count": node_count,
                "edge_count": edge_count,
                "internal_edge_count": max(0, edge_count - rng.randint(5, 25)),
                "external_edge_count": rng.randint(3, 28),
                "representative_node_ids": tuple(
                    f"{cluster_id}:node:{node_index:04d}" for node_index in range(8)
                ),
                "hub_node_ids": tuple(
                    f"{cluster_id}:hub:{hub_index:02d}" for hub_index in range(3)
                ),
                "bridge_node_ids": tuple(
                    f"{cluster_id}:bridge:{bridge_index:02d}"
                    for bridge_index in range(2)
                ),
                "warning_count": 1 if index % 17 == 0 else 0,
                "source_kinds": (kind, _NODE_KINDS[(index + 3) % len(_NODE_KINDS)]),
                "centroid_hint": {
                    "x": round(0.5 + rng.uniform(-0.45, 0.45), 4),
                    "y": round(0.5 + rng.uniform(-0.45, 0.45), 4),
                },
                "color_hint": _color_hint(index),
                "freshness": "fresh" if index % 5 else "changed",
                "omitted": max(0, node_count - 8),
                "expansion_cursor": f"{scenario}:{cluster_id}:offset:0",
            }
        )
    return tuple(clusters)


def _fixture_cluster_node_counts(
    rng: random.Random,
    raw_node_count: int,
    cluster_count: int,
) -> tuple[int, ...]:
    minimum = 100
    if raw_node_count < cluster_count * minimum:
        raise ValueError(
            "fixture cluster count requires at least 100 nodes per cluster"
        )
    remaining = raw_node_count - cluster_count * minimum
    weights = [rng.randint(8, 24) for _ in range(cluster_count)]
    weight_total = sum(weights)
    counts = [minimum + int(remaining * weight / weight_total) for weight in weights]
    drift = raw_node_count - sum(counts)
    for index in range(abs(drift)):
        counts[index % cluster_count] += 1 if drift > 0 else -1
    return tuple(counts)


def _fixture_nodes(
    rng: random.Random,
    clusters: tuple[Mapping[str, Any], ...],
    node_budget: int,
) -> tuple[Mapping[str, Any], ...]:
    nodes: list[Mapping[str, Any]] = []
    for cluster in clusters:
        if len(nodes) >= node_budget:
            break
        for local_index, node_id in enumerate(cluster["representative_node_ids"]):
            if len(nodes) >= node_budget:
                break
            kind = _NODE_KINDS[(local_index + len(nodes)) % len(_NODE_KINDS)]
            nodes.append(
                {
                    "id": node_id,
                    "label": f"{kind.title()} {cluster['label']}:{local_index:02d}",
                    "kind": kind,
                    "source_kind": kind,
                    "cluster_id": cluster["id"],
                    "summary": f"Synthetic {kind} graph item in {cluster['label']}.",
                    "degree": rng.randint(1, 24),
                    "confidence": round(rng.uniform(0.62, 0.99), 3),
                    "freshness": cluster["freshness"],
                    "evidence_count": rng.randint(0, 4),
                    "provenance_count": rng.randint(1, 3),
                    "include_reason": "representative",
                }
            )
    return tuple(nodes)


def _fixture_edges(
    rng: random.Random,
    nodes: tuple[Mapping[str, Any], ...],
    clusters: tuple[Mapping[str, Any], ...],
    edge_budget: int,
) -> tuple[Mapping[str, Any], ...]:
    if len(nodes) < 2:
        return ()
    nodes_by_cluster: dict[str, list[Mapping[str, Any]]] = {}
    for node in nodes:
        nodes_by_cluster.setdefault(str(node["cluster_id"]), []).append(node)
    cluster_ids = [str(cluster["id"]) for cluster in clusters]
    edges: list[Mapping[str, Any]] = []
    for cluster_id, cluster_nodes in sorted(nodes_by_cluster.items()):
        for index, source in enumerate(cluster_nodes[:-1]):
            if len(edges) >= edge_budget:
                break
            target = cluster_nodes[index + 1]
            edges.append(_fixture_edge_record(source, target, len(edges), rng))
        if len(edges) >= edge_budget:
            break
        source = cluster_nodes[-1]
        target_cluster = cluster_ids[
            (cluster_ids.index(cluster_id) + rng.randint(1, 5)) % len(cluster_ids)
        ]
        target_candidates = nodes_by_cluster.get(target_cluster) or list(nodes)
        target = rng.choice(target_candidates)
        edges.append(_fixture_edge_record(source, target, len(edges), rng))
    return tuple(edges[:edge_budget])


def _fixture_edge_record(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    index: int,
    rng: random.Random,
) -> Mapping[str, Any]:
    kind = _EDGE_KINDS[index % len(_EDGE_KINDS)]
    return {
        "id": f"edge:{index:06d}",
        "source_id": source["id"],
        "target_id": target["id"],
        "kind": kind,
        "confidence": round(rng.uniform(0.6, 0.98), 3),
        "freshness": "fresh" if index % 7 else "changed",
    }


def _fixture_edge_bundles(
    rng: random.Random,
    clusters: tuple[Mapping[str, Any], ...],
    edge_budget: int,
) -> tuple[Mapping[str, Any], ...]:
    bundles: dict[str, dict[str, Any]] = {}
    max_bundles = min(edge_budget, len(clusters) * 2)
    for index in range(max_bundles):
        source = clusters[index % len(clusters)]
        target = clusters[(index * 7 + 3) % len(clusters)]
        if source["id"] == target["id"]:
            continue
        bundle_id = f"bundle:{source['id']}:{target['id']}"
        edge_kind_counts = {
            _EDGE_KINDS[index % len(_EDGE_KINDS)]: rng.randint(4, 120),
            _EDGE_KINDS[(index + 1) % len(_EDGE_KINDS)]: rng.randint(2, 80),
        }
        edge_count = sum(edge_kind_counts.values())
        if bundle_id in bundles:
            bundle = bundles[bundle_id]
            bundle["edge_count"] += edge_count
            counts = bundle["edge_kind_counts"]
            for kind, count in edge_kind_counts.items():
                counts[kind] = counts.get(kind, 0) + count
            continue
        bundles[bundle_id] = {
            "id": bundle_id,
            "source_cluster_id": source["id"],
            "target_cluster_id": target["id"],
            "edge_count": edge_count,
            "edge_kind_counts": edge_kind_counts,
            "representative_edge_ids": (f"edge:{index:06d}",),
            "omitted_reason": "bundle_budget",
        }
    return tuple(sorted(bundles.values(), key=lambda item: str(item["id"])))


def _find_cluster(
    envelope: ViewerGraphEnvelope,
    cluster_id: str,
) -> Mapping[str, Any]:
    for cluster in envelope.clusters:
        if cluster.get("id") == cluster_id:
            return cluster
    raise KeyError(f"viewer cluster id not found: {cluster_id}")


def _capabilities() -> Mapping[str, Any]:
    return {
        "content_preview": True,
        "full_content_lookup": True,
        "cluster_expand": True,
        "neighborhood": True,
        "path": True,
        "edit_commands": ("note_draft", "tag_draft", "pin_draft", "evidence_request"),
        "durable_mutation": False,
    }


def _compatibility() -> Mapping[str, Any]:
    return {
        "viewer": "graphfakos",
        "static_fallback": True,
        "requires_pragmagraph_import_in_viewer": False,
        "large_raw_nodes_embedded_by_default": False,
    }


def _color_hint(index: int) -> str:
    palette = ("#45d1c6", "#7cc957", "#9e7cff", "#ff9b52", "#6ab3ff", "#ef6f82")
    return palette[index % len(palette)]


__all__ = [
    "VIEWER_ENVELOPE_SCHEMA_VERSION",
    "VIEWER_FIXTURE_SCENARIOS",
    "ViewerGraphEnvelope",
    "build_viewer_envelope",
    "build_viewer_fixture_envelope",
    "explain_omitted",
    "load_viewer_envelope",
    "viewer_cluster",
    "viewer_content",
    "viewer_neighborhood",
    "viewer_path",
    "write_viewer_envelope",
]
