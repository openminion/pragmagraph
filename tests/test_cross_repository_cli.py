from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pragmagraph.__main__ import main
from pragmagraph.contracts import EDGE_RESOLVES_TO, NODE_PROJECT, NODE_SYMBOL
from pragmagraph.export import project_snapshot
from pragmagraph.graphify import snapshot_from_graphify_payload, to_graphify_payload
from pragmagraph.models import GraphNode, GraphSnapshot, PragmaGraphError, SourceRef
from pragmagraph.portability import node_id
from pragmagraph.refresh import build_ci_delta
from pragmagraph.server.backend import ServiceConfig, build_wired_registry
from pragmagraph.server.server import ServerInfo, dispatch
from pragmagraph.server.tools import SUPPORTED_TOOL_NAMES
from pragmagraph.storage import (
    SQLiteGraphStore,
    load_snapshot,
    save_snapshot,
    stable_dumps,
)
from pragmagraph.workspace import NamedSnapshot, compose_snapshots

SYMBOL = "scip-python python example-service 1.0.0 example/service#serve()."


def _snapshot(namespace: str, *, external: bool) -> GraphSnapshot:
    project = GraphNode(
        id=node_id(namespace, NODE_PROJECT, "."),
        kind=NODE_PROJECT,
        label=namespace,
        source_ref=SourceRef(path="."),
    )
    symbol = GraphNode(
        id=node_id(namespace, NODE_SYMBOL, "service"),
        kind=NODE_SYMBOL,
        label="serve",
        source_ref=SourceRef(
            path="" if external else "src/service.py",
            line=None if external else 3,
        ),
        metadata={"scip_symbol": SYMBOL, "scip_external": external},
    )
    return GraphSnapshot(namespace=namespace, root_path="", nodes=(project, symbol))


def _composed() -> GraphSnapshot:
    return compose_snapshots(
        (
            NamedSnapshot("consumer", _snapshot("consumer", external=True)),
            NamedSnapshot("provider", _snapshot("provider", external=False)),
        )
    ).snapshot


def _call(registry, method: str, params=None):
    return dispatch(
        {"jsonrpc": "2.0", "id": method, "method": method, "params": params or {}},
        registry=registry,
        server_info=ServerInfo(),
    )


def test_multi_root_compose_cli_writes_atomic_canonical_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    consumer_path = tmp_path / "consumer.json"
    provider_path = tmp_path / "provider.json"
    output_path = tmp_path / "workspace.json"
    save_snapshot(_snapshot("consumer", external=True), consumer_path)
    save_snapshot(_snapshot("provider", external=False), provider_path)

    exit_code = main(
        [
            "multi-root-compose",
            "--snapshot",
            f"consumer={consumer_path}",
            "--snapshot",
            f"provider={provider_path}",
            "--out",
            str(output_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    restored = load_snapshot(output_path)

    assert exit_code == 0
    assert payload["report"]["outcome_counts"]["cross_repo_definition_exact"] == 1
    assert sum(edge.kind == EDGE_RESOLVES_TO for edge in restored.edges) == 1


def test_failed_cli_composition_preserves_existing_output(tmp_path: Path) -> None:
    nested_path = tmp_path / "nested.json"
    output_path = tmp_path / "workspace.json"
    nested = replace(
        _snapshot("nested", external=False),
        stats={"cross_repo_resolution_schema_version": "existing"},
    )
    save_snapshot(nested, nested_path)
    output_path.write_text("existing-output\n", encoding="utf-8")

    with pytest.raises(PragmaGraphError) as exc:
        main(
            [
                "multi-root-compose",
                "--snapshot",
                f"nested={nested_path}",
                "--out",
                str(output_path),
            ]
        )

    assert exc.value.code == "NESTED_SNAPSHOT_COMPOSITION"
    assert output_path.read_text(encoding="utf-8") == "existing-output\n"
    assert not tuple(tmp_path.glob(".workspace.json.*.tmp"))


def test_service_and_mcp_read_composed_facts_without_compose_operation(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "workspace.json"
    save_snapshot(_composed(), snapshot_path)
    registry = build_wired_registry(ServiceConfig(snapshot_path=str(snapshot_path)))

    status = _call(registry, "resources/read", {"uri": "pragma://status"})
    tools = _call(registry, "tools/list")
    payload = json.loads(status["result"]["contents"][0]["text"])
    names = [item["name"] for item in tools["result"]["tools"]]

    assert payload["snapshot_stats"]["root_count"] == 2
    assert (
        payload["snapshot_stats"]["cross_repo_resolution"]["outcome_counts"][
            "cross_repo_definition_exact"
        ]
        == 1
    )
    assert set(names) == set(SUPPORTED_TOOL_NAMES)
    assert not any("compose" in name for name in names)


def test_resolution_facts_round_trip_through_storage_export_graphify_and_delta(
    tmp_path: Path,
) -> None:
    snapshot = _composed()
    resolution = next(edge for edge in snapshot.edges if edge.kind == EDGE_RESOLVES_TO)
    json_path = tmp_path / "workspace.json"
    save_snapshot(snapshot, json_path)
    restored_json = load_snapshot(json_path)
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "workspace.sqlite")
    restored_sqlite = store.export_snapshot()
    graphify = snapshot_from_graphify_payload(to_graphify_payload(snapshot))
    portable = project_snapshot(snapshot, profile="portable").snapshot
    before = replace(
        snapshot,
        edges=tuple(edge for edge in snapshot.edges if edge.id != resolution.id),
    )
    delta = build_ci_delta(before, snapshot)
    delta_store = SQLiteGraphStore.from_snapshot(before, tmp_path / "delta.sqlite")
    delta_store.apply_snapshot_delta(snapshot)

    assert stable_dumps(restored_json) == stable_dumps(snapshot)
    assert stable_dumps(restored_sqlite) == stable_dumps(snapshot)
    assert (
        next(edge for edge in graphify.edges if edge.id == resolution.id).metadata[
            "resolution_kind"
        ]
        == "exact_scip_symbol"
    )
    portable_ids = {node.id for node in portable.nodes}
    assert all(
        edge.source_id in portable_ids and edge.target_id in portable_ids
        for edge in portable.edges
    )
    assert resolution.id in delta.structural.added_edge_ids
    assert stable_dumps(delta_store.export_snapshot()) == stable_dumps(snapshot)
