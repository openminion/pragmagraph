"""Deterministic synthetic viewer envelope fixtures."""

from __future__ import annotations

import random
from typing import Any, Mapping

from pragmagraph.viewer.envelope import (
    DEFAULT_GENERATED_AT,
    VIEWER_ENVELOPE_SCHEMA_VERSION,
    VIEWER_FIXTURE_SCENARIOS,
    ViewerGraphEnvelope,
    color_hint,
    viewer_capabilities,
    viewer_compatibility,
)

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
    omitted = _fixture_omitted_records(
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
        generated_at=DEFAULT_GENERATED_AT,
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
        expansion=_fixture_expansion_records(clusters),
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
                "observed_at": DEFAULT_GENERATED_AT,
            }
            for node in visible_nodes
        ),
        capabilities=viewer_capabilities(),
        compatibility=viewer_compatibility(),
    )


def _fixture_omitted_records(
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


def _fixture_expansion_records(
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
                "color_hint": color_hint(index),
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
