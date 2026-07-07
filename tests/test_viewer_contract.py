from __future__ import annotations

import json
import subprocess
import sys

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.viewer import (
    VIEWER_ENVELOPE_SCHEMA_VERSION,
    ViewerGraphEnvelope,
    build_viewer_envelope,
    build_viewer_fixture_envelope,
    viewer_cluster,
    viewer_content,
)


def _snapshot() -> GraphSnapshot:
    nodes = tuple(
        GraphNode(
            id=f"node:{index:03d}",
            kind="file" if index % 2 else "symbol",
            label=f"Node {index:03d}",
            source_ref=SourceRef(path=f"src/module_{index % 5}.py", line=index + 1),
            text=f"Observed source content {index}.",
            metadata={"freshness": "fresh", "confidence": 0.9},
        )
        for index in range(40)
    )
    edges = tuple(
        GraphEdge(
            id=f"edge:{index:03d}",
            kind="references",
            source_id=f"node:{index:03d}",
            target_id=f"node:{(index + 1) % 40:03d}",
        )
        for index in range(60)
    )
    return GraphSnapshot(
        namespace="viewer-demo",
        root_path="/repo",
        nodes=nodes,
        edges=edges,
        created_at="2026-07-06T00:00:00+00:00",
    )


def test_viewer_envelope_round_trip_and_omitted_counts() -> None:
    envelope = build_viewer_envelope(
        _snapshot(),
        level_of_detail="cluster",
        node_budget=12,
        edge_budget=8,
        cluster_size=8,
    )
    payload = envelope.to_dict()
    rebuilt = ViewerGraphEnvelope.from_dict(payload)

    assert rebuilt.schema_version == VIEWER_ENVELOPE_SCHEMA_VERSION
    assert rebuilt.level_of_detail == "cluster"
    assert rebuilt.graph_stats["raw_node_count"] == 40
    assert len(rebuilt.nodes) == 12
    assert rebuilt.omitted[0]["reason"] == "node_budget"
    assert rebuilt.capabilities["durable_mutation"] is False


def test_large_viewer_fixture_is_bounded_and_deterministic() -> None:
    first = build_viewer_fixture_envelope("viewer-scale-1m", node_budget=120)
    second = build_viewer_fixture_envelope("viewer-scale-1m", node_budget=120)

    assert first.to_dict() == second.to_dict()
    assert first.graph_stats["raw_node_count"] == 1_000_000
    assert first.graph_stats["minimum_raw_nodes_per_cluster"] >= 100
    assert sum(int(cluster["node_count"]) for cluster in first.clusters) == 1_000_000
    assert all(
        int(bundle["edge_count"])
        == sum(int(count) for count in bundle["edge_kind_counts"].values())
        for bundle in first.edge_bundles
    )
    assert len(first.nodes) == 120
    assert first.level_of_detail == "meta"
    assert first.omitted[0]["count"] == 999_880


def test_viewer_cluster_and_content_helpers_are_bounded() -> None:
    envelope = build_viewer_fixture_envelope("viewer-scale-1k", node_budget=80)
    cluster_id = str(envelope.clusters[0]["id"])
    node_id = str(envelope.nodes[0]["id"])

    cluster = viewer_cluster(envelope, cluster_id, budget=3)
    content = viewer_content(envelope, node_id, mode="full")

    assert cluster["cluster"]["id"] == cluster_id
    assert len(cluster["nodes"]) <= 3
    assert content["node_id"] == node_id
    assert content["content"]["mode"] == "full"
    assert "provider-owned" in content["content"]["text"]


def test_viewer_fixture_cli_writes_provider_envelope(tmp_path) -> None:
    out = tmp_path / "viewer-scale-200k.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "viewer-fixture",
            "--scenario",
            "viewer-scale-200k",
            "--node-budget",
            "60",
            "--out",
            str(out),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    envelope = json.loads(out.read_text(encoding="utf-8"))

    assert payload["raw_node_count"] == 200_000
    assert payload["visible_node_count"] == 60
    assert envelope["schema_version"] == VIEWER_ENVELOPE_SCHEMA_VERSION
    assert envelope["graph_stats"]["minimum_raw_nodes_per_cluster"] >= 100

    cluster_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "viewer-cluster",
            str(out),
            "scale-001",
            "--budget",
            "3",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    content_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "viewer-content",
            str(out),
            "scale-001:node:0000",
            "--mode",
            "preview",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(cluster_result.stdout)["cluster"]["id"] == "scale-001"
    assert json.loads(content_result.stdout)["node_id"] == "scale-001:node:0000"
