from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.graphify import to_graphify_payload
from pragmagraph.models import QueryRequest
from pragmagraph.service import (
    METHOD_CAPABILITIES,
    METHOD_QUERY,
    METHOD_SHUTDOWN,
    LocalQueryService,
    ServiceRequest,
)
from pragmagraph.storage import (
    JsonSnapshotStore,
    SQLiteGraphStore,
    load_snapshot,
    save_snapshot,
    stable_dumps,
)

from .package_paths import build_fixture_repo


def _store_fixture_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        repo_name="store-repo",
        files={
            "README.md": "# Store Graph\n\nSee `src/app.py`.\n",
            "docs/guide.md": "## Store Guide\n\nRuntimeGraph references static facts.\n",
            "src/app.py": (
                "from helper import build_value\n\n"
                "class RuntimeGraph:\n"
                "    pass\n\n"
                "def run():\n"
                "    return build_value()\n"
            ),
            "src/helper.py": "def build_value():\n    return 7\n",
        },
    )


def _snapshot(tmp_path: Path):
    return index_path(_store_fixture_root(tmp_path), namespace="store-fixture")


def _serve_process(*args: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "pragmagraph", "serve", *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _roundtrip(
    proc: subprocess.Popen[str],
    payload: dict[str, object],
) -> dict[str, object]:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def test_json_snapshot_store_is_canonical_query_oracle(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    store = JsonSnapshotStore(snapshot)

    exported = store.export_snapshot()
    result = store.query(QueryRequest(query="RuntimeGraph"))

    assert stable_dumps(exported) == stable_dumps(snapshot)
    assert result.hits[0].node.label == "RuntimeGraph"
    assert store.capabilities().to_dict()["backend"] == "json"
    assert "materialized_sql" in store.capabilities().unsupported_modes


def test_sqlite_store_round_trips_snapshot_and_reports_capabilities(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path)
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "graph.sqlite")

    exported = store.export_snapshot()
    manifest = store.manifest()
    capabilities = store.capabilities()

    assert stable_dumps(exported) == stable_dumps(snapshot)
    assert manifest.backend == "sqlite"
    assert manifest.node_count == len(snapshot.nodes)
    assert manifest.edge_count == len(snapshot.edges)
    assert manifest.source_ref_count == len(snapshot.nodes) + len(snapshot.edges)
    assert capabilities.query_supported is True
    assert "vector" in capabilities.unsupported_modes


def test_sqlite_store_query_neighborhood_and_path_match_snapshot_oracle(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path)
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "graph.sqlite")
    oracle = JsonSnapshotStore(snapshot)
    runtime_node = next(node for node in snapshot.nodes if node.label == "RuntimeGraph")
    guide_node = next(
        node for node in snapshot.nodes if node.source_ref.path == "docs/guide.md"
    )

    store_query = store.query(QueryRequest(query="RuntimeGraph", max_results=5))
    oracle_query = oracle.query(QueryRequest(query="RuntimeGraph", max_results=5))
    store_neighborhood = store.neighborhood(runtime_node.id, depth=2, max_results=5)
    store_path = store.path(runtime_node.id, guide_node.id, max_hops=4)

    assert [hit.node.id for hit in store_query.hits] == [
        hit.node.id for hit in oracle_query.hits
    ]
    assert store_query.diagnostics["store_backend"] == "sqlite"
    assert isinstance(store_query.diagnostics["candidate_node_ids"], list)
    assert store_neighborhood.query == runtime_node.id
    assert store_path.source_id == runtime_node.id
    assert store_path.target_id == guide_node.id


def test_cli_store_import_query_export_and_health(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    store_path = tmp_path / "graph.sqlite"
    exported_path = tmp_path / "exported.json"
    save_snapshot(_snapshot(tmp_path), snapshot_path)

    import_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "store-import",
                str(snapshot_path),
                "--out",
                str(store_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    query_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "store-query",
                str(store_path),
                "RuntimeGraph",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    export_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "store-export",
                str(store_path),
                "--out",
                str(exported_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    health_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "store-health",
                str(store_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    assert import_payload["manifest"]["backend"] == "sqlite"
    assert query_payload["hits"][0]["node"]["label"] == "RuntimeGraph"
    assert export_payload["ok"] is True
    assert load_snapshot(exported_path).namespace == "store-fixture"
    assert health_payload["capabilities"]["import_export_supported"] is True


def test_graphify_payload_round_trips_through_sqlite_store(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "graph.sqlite")

    exported_payload = to_graphify_payload(store.export_snapshot())
    snapshot_payload = to_graphify_payload(snapshot)

    assert exported_payload["nodes"] == snapshot_payload["nodes"]
    assert exported_payload["edges"] == snapshot_payload["edges"]
    assert exported_payload["omitted"] == snapshot_payload["omitted"]


def test_service_can_start_from_store_backend(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    store_path = tmp_path / "graph.sqlite"
    SQLiteGraphStore.from_snapshot(snapshot, store_path)
    service = LocalQueryService.from_store_path(store_path)

    capabilities = service.handle_request(
        ServiceRequest(id="c1", method=METHOD_CAPABILITIES, params={})
    )[0]
    query_response = service.handle_request(
        ServiceRequest(id="q1", method=METHOD_QUERY, params={"text": "RuntimeGraph"})
    )[0]

    assert capabilities.to_dict()["result"]["startup_mode"] == "store"
    assert capabilities.to_dict()["result"]["store_backend"] == "sqlite"
    assert (
        query_response.to_dict()["result"]["hits"][0]["node"]["label"] == "RuntimeGraph"
    )


def test_stdio_service_can_start_from_store_backend(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    store_path = tmp_path / "graph.sqlite"
    SQLiteGraphStore.from_snapshot(snapshot, store_path)

    proc = _serve_process("--store", str(store_path))
    try:
        capabilities = _roundtrip(proc, {"id": "1", "method": METHOD_CAPABILITIES})
        query_response = _roundtrip(
            proc,
            {"id": "2", "method": METHOD_QUERY, "params": {"text": "RuntimeGraph"}},
        )
        _roundtrip(proc, {"id": "3", "method": METHOD_SHUTDOWN})
    finally:
        proc.wait(timeout=5)

    assert capabilities["result"]["startup_mode"] == "store"
    assert capabilities["result"]["store_backend"] == "sqlite"
    assert query_response["result"]["diagnostics"]["store_backend"] == "sqlite"
    assert proc.returncode == 0
