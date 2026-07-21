from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.models import QueryRequest
from pragmagraph.interchange import load_native_scip
from pragmagraph.query import query
from pragmagraph.service import (
    ERROR_INVALID_PARAMS,
    ERROR_INVALID_REQUEST,
    ERROR_REFRESH_UNSUPPORTED,
    ERROR_UNSUPPORTED_METHOD,
    METHOD_CAPABILITIES,
    METHOD_QUERY,
    METHOD_REFRESH,
    METHOD_SHUTDOWN,
    METHOD_STATUS,
    LocalQueryService,
    ServiceRequest,
    request_from_json_line,
)
from pragmagraph.storage import save_snapshot
from .package_paths import build_fixture_repo
from .scip_fixtures import TYPESCRIPT_SCIP


def _repo_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        files={
            "README.md": "# Runtime Graph\n\n## Usage\n\nStatic facts only.\n",
            "src/app.py": (
                "class RuntimeGraph:\n"
                "    pass\n\n"
                "def build_runtime_graph():\n"
                "    return RuntimeGraph()\n"
            ),
        },
    )


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


def test_snapshot_service_keeps_loaded_state_and_rejects_refresh(
    tmp_path: Path,
) -> None:
    root = _repo_root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(index_path(root, namespace="fixture"), snapshot_path)
    service = LocalQueryService.from_snapshot_path(snapshot_path)

    first = service.handle_request(
        ServiceRequest(id="q1", method=METHOD_QUERY, params={"text": "RuntimeGraph"})
    )[0]
    assert first.ok is True
    assert first.to_dict()["result"]["hits"][0]["node"]["label"] == "RuntimeGraph"

    mutated_root = tmp_path / "other"
    (mutated_root / "src").mkdir(parents=True)
    (mutated_root / "src" / "other.py").write_text(
        "class OtherGraph:\n    pass\n",
        encoding="utf-8",
    )
    save_snapshot(index_path(mutated_root, namespace="fixture"), snapshot_path)

    second = service.handle_request(
        ServiceRequest(id="q2", method=METHOD_QUERY, params={"text": "RuntimeGraph"})
    )[0]
    assert second.ok is True
    assert second.to_dict()["result"]["hits"][0]["node"]["label"] == "RuntimeGraph"

    refresh = service.handle_request(
        ServiceRequest(id="r1", method=METHOD_REFRESH, params={})
    )[0]
    assert refresh.ok is False
    assert refresh.to_dict()["error"]["code"] == ERROR_REFRESH_UNSUPPORTED

    status = service.handle_request(
        ServiceRequest(id="s1", method=METHOD_STATUS, params={})
    )[0].to_dict()["result"]
    assert status["refresh_readiness"] == {
        "can_refresh": False,
        "startup_mode": "snapshot",
        "reason": "snapshot_backed_refresh_unsupported",
        "root_path_present": True,
    }
    assert status["artifact_presence"]["snapshot"] is True
    assert status["last_refresh"] is None


def test_service_capabilities_expose_native_scip_and_loaded_report(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "precise.json"
    save_snapshot(load_native_scip(TYPESCRIPT_SCIP).snapshot, snapshot_path)
    service = LocalQueryService.from_snapshot_path(snapshot_path)

    capabilities = service.capabilities().to_dict()
    health_result = service.handle_request(
        ServiceRequest(id="health", method="health", params={})
    )[0].to_dict()["result"]

    assert capabilities["native_scip_available"] is True
    assert capabilities["precise_ingestion_loaded"] is True
    assert capabilities["precise_producer"] == "scip-typescript"
    assert health_result["service"]["precise_ingestion"]["producer"]["name"] == (
        "scip-typescript"
    )


def test_root_service_refresh_updates_state_and_persists_outputs(
    tmp_path: Path,
) -> None:
    root = _repo_root(tmp_path)
    snapshot_out = tmp_path / "service-snapshot.json"
    manifest_out = tmp_path / "service-manifest.json"
    service = LocalQueryService.from_root(
        root,
        namespace="fixture",
        snapshot_out_path=snapshot_out,
        manifest_out_path=manifest_out,
    )

    baseline = query(service.snapshot, QueryRequest(query="OperatorGraph"))
    assert baseline.hits == ()
    assert snapshot_out.is_file()
    assert manifest_out.is_file()
    status_before = service.status().to_dict()
    assert status_before["refresh_readiness"]["can_refresh"] is True
    assert status_before["refresh_readiness"]["reason"] == (
        "root_backed_explicit_refresh_available"
    )
    assert status_before["artifact_presence"]["snapshot"] is True
    assert status_before["artifact_presence"]["manifest"] is True
    assert status_before["last_refresh"]["status"] == "fresh"

    (root / "src" / "ops.py").write_text(
        "class OperatorGraph:\n    pass\n",
        encoding="utf-8",
    )
    response = service.handle_request(
        ServiceRequest(id="refresh", method=METHOD_REFRESH, params={})
    )[0]

    assert response.ok is True
    payload = response.to_dict()["result"]
    assert "src/ops.py" in payload["changed_paths"]
    assert payload["path_changes"]
    assert payload["snapshot_delta"]["added_node_ids"]
    latest = query(service.snapshot, QueryRequest(query="OperatorGraph"))
    assert latest.hits[0].node.label == "OperatorGraph"
    assert snapshot_out.is_file()
    assert manifest_out.is_file()
    status_after = service.handle_request(
        ServiceRequest(id="status", method=METHOD_STATUS, params={})
    )[0].to_dict()["result"]
    assert status_after["last_refresh"]["changed_path_count"] >= 1
    assert status_after["graph"]["node_count"] == len(service.snapshot.nodes)


def test_service_stdio_runner_supports_snapshot_sessions(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(index_path(root, namespace="fixture"), snapshot_path)

    proc = _serve_process("--snapshot", str(snapshot_path))
    try:
        capabilities = _roundtrip(proc, {"id": "1", "method": METHOD_CAPABILITIES})
        status = _roundtrip(proc, {"id": "status", "method": METHOD_STATUS})
        first = _roundtrip(
            proc,
            {"id": "2", "method": METHOD_QUERY, "params": {"text": "RuntimeGraph"}},
        )
        second = _roundtrip(
            proc,
            {"id": "3", "method": METHOD_QUERY, "params": {"text": "RuntimeGraph"}},
        )
        shutdown = _roundtrip(proc, {"id": "4", "method": METHOD_SHUTDOWN})
    finally:
        proc.wait(timeout=5)

    assert capabilities["result"]["startup_mode"] == "snapshot"
    assert capabilities["result"]["refresh_supported"] is False
    assert capabilities["result"]["export_schema_version"].startswith(
        "pragmagraph.export."
    )
    assert capabilities["result"]["snapshot_id"]
    assert capabilities["result"]["parser_set"]
    assert capabilities["result"]["parser_versions"]
    assert status["result"]["refresh_readiness"]["can_refresh"] is False
    assert status["result"]["artifact_presence"]["snapshot"] is True
    assert first["result"] == second["result"]
    assert shutdown["result"]["shutdown"] == "accepted"
    assert proc.returncode == 0


def test_service_stdio_runner_supports_root_refresh_sessions(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    proc = _serve_process("--root", str(root), "--namespace", "fixture")
    try:
        initial = _roundtrip(
            proc,
            {"id": "1", "method": METHOD_QUERY, "params": {"text": "OperatorGraph"}},
        )
        (root / "src" / "ops.py").write_text(
            "class OperatorGraph:\n    pass\n",
            encoding="utf-8",
        )
        refreshed = _roundtrip(proc, {"id": "2", "method": METHOD_REFRESH})
        queried = _roundtrip(
            proc,
            {"id": "3", "method": METHOD_QUERY, "params": {"text": "OperatorGraph"}},
        )
        _roundtrip(proc, {"id": "4", "method": METHOD_SHUTDOWN})
    finally:
        proc.wait(timeout=5)

    assert initial["result"]["hits"] == []
    assert "src/ops.py" in refreshed["result"]["changed_paths"]
    assert refreshed["result"]["path_changes"]
    assert queried["result"]["hits"][0]["node"]["label"] == "OperatorGraph"
    assert proc.returncode == 0


def test_service_workspace_startup_uses_persisted_workspace(tmp_path: Path) -> None:
    from pragmagraph.workspace import initialize_workspace

    root = _repo_root(tmp_path)
    workspace = tmp_path / "workspace"
    initialize_workspace(
        label="demo",
        root_path=root,
        workspace_path=workspace,
        namespace="fixture",
    )

    proc = _serve_process("--workspace", str(workspace))
    try:
        capabilities = _roundtrip(proc, {"id": "1", "method": METHOD_CAPABILITIES})
        query_result = _roundtrip(
            proc,
            {"id": "2", "method": METHOD_QUERY, "params": {"text": "RuntimeGraph"}},
        )
        _roundtrip(proc, {"id": "3", "method": METHOD_SHUTDOWN})
    finally:
        proc.wait(timeout=5)

    assert capabilities["result"]["startup_mode"] == "workspace"
    assert capabilities["result"]["refresh_supported"] is True
    assert capabilities["result"]["workspace_path"] == str(workspace.resolve())
    assert query_result["result"]["hits"][0]["node"]["label"] == "RuntimeGraph"


def test_service_invalid_requests_return_typed_errors(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(index_path(root, namespace="fixture"), snapshot_path)
    service = LocalQueryService.from_snapshot_path(snapshot_path)

    assert request_from_json_line('{"id":"1","method":"health"}').method == "health"

    invalid_json = None
    try:
        request_from_json_line("{bad json")
    except Exception as exc:  # pragma: no cover - assertion uses captured value
        invalid_json = exc
    assert getattr(invalid_json, "code") == ERROR_INVALID_REQUEST

    unsupported = service.handle_request(
        ServiceRequest(id="u1", method="unknown", params={})
    )[0]
    invalid_params = service.handle_request(
        ServiceRequest(id="u2", method=METHOD_QUERY, params={"max_results": 0})
    )[0]

    assert unsupported.ok is False
    assert unsupported.to_dict()["error"]["code"] == ERROR_UNSUPPORTED_METHOD
    assert invalid_params.ok is False
    assert invalid_params.to_dict()["error"]["code"] == ERROR_INVALID_PARAMS


def test_service_health_and_export_surface_richer_metadata(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(index_path(root, namespace="fixture"), snapshot_path)
    service = LocalQueryService.from_snapshot_path(snapshot_path)

    health_response = service.handle_request(
        ServiceRequest(id="h1", method="health", params={})
    )[0]
    export_response = service.handle_request(
        ServiceRequest(id="e1", method="export", params={"format": "dot"})
    )[0]

    assert health_response.ok is True
    assert health_response.to_dict()["result"]["service"]["snapshot_id"]
    assert "diagnostic_counts" in health_response.to_dict()["result"]["service"]
    assert health_response.to_dict()["result"]["service"]["parser_versions"]
    assert export_response.ok is True
    assert export_response.to_dict()["result"]["export_schema_version"].startswith(
        "pragmagraph.export."
    )
