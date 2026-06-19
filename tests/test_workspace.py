from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.models import QueryRequest
from pragmagraph.query import query
from pragmagraph.service import (
    LocalQueryService,
    METHOD_QUERY,
    METHOD_REFRESH,
    METHOD_SHUTDOWN,
    ServiceRequest,
)
from pragmagraph.workspace import (
    initialize_workspace,
    load_workspace_status,
)
from .package_paths import build_fixture_repo


def _repo_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        files={
            "README.md": "# Runtime Graph\n",
            "src/app.py": "class RuntimeGraph:\n    pass\n",
        },
    )


def test_workspace_init_persists_expected_files_and_status(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    workspace = tmp_path / "workspace"

    result = initialize_workspace(
        label="demo",
        root_path=root,
        workspace_path=workspace,
        namespace="fixture",
    )

    assert Path(result.workspace.paths.metadata_path).is_file()
    assert Path(result.workspace.paths.profile_path).is_file()
    assert Path(result.workspace.paths.snapshot_path).is_file()
    assert Path(result.workspace.paths.manifest_path).is_file()
    assert Path(result.workspace.paths.status_path).is_file()
    assert result.operation.status.status == "fresh"

    status = load_workspace_status(workspace)
    assert status.workspace.label == "demo"
    assert status.workspace.namespace == "fixture"
    assert status.snapshot_present is True
    assert status.manifest_present is True
    assert status.profile_present is True
    assert status.refresh_status is not None
    assert status.refresh_status.status == "fresh"


def test_workspace_refresh_and_service_reuse_persisted_state(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    workspace = tmp_path / "workspace"
    initialize_workspace(
        label="demo",
        root_path=root,
        workspace_path=workspace,
        namespace="fixture",
    )

    service = LocalQueryService.from_workspace(workspace)
    baseline = query(service.snapshot, QueryRequest(query="OperatorGraph"))
    assert baseline.hits == ()

    (root / "src" / "ops.py").write_text(
        "class OperatorGraph:\n    pass\n",
        encoding="utf-8",
    )
    refreshed = service.handle_request(
        ServiceRequest(id="r1", method=METHOD_REFRESH, params={})
    )[0].to_dict()["result"]

    assert "src/ops.py" in refreshed["changed_paths"]
    latest = query(service.snapshot, QueryRequest(query="OperatorGraph"))
    assert latest.hits[0].node.label == "OperatorGraph"

    status = load_workspace_status(workspace)
    assert status.refresh_status is not None
    assert status.refresh_status.changed_path_count >= 1


def test_cli_workspace_commands_and_workspace_service(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    workspace = tmp_path / "workspace"

    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "workspace-init",
            str(root),
            "--workspace",
            str(workspace),
            "--label",
            "demo",
            "--namespace",
            "fixture",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    init_payload = json.loads(init.stdout)
    assert init_payload["workspace"]["label"] == "demo"

    status = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "workspace-status",
            str(workspace),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status_payload = json.loads(status.stdout)
    assert status_payload["snapshot_present"] is True

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "serve",
            "--workspace",
            str(workspace),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdin is not None
        assert proc.stdout is not None
        proc.stdin.write(
            json.dumps(
                {"id": "1", "method": METHOD_QUERY, "params": {"text": "RuntimeGraph"}}
            )
            + "\n"
        )
        proc.stdin.flush()
        query_payload = json.loads(proc.stdout.readline())
        assert query_payload["result"]["hits"][0]["node"]["label"] == "RuntimeGraph"

        proc.stdin.write(json.dumps({"id": "2", "method": METHOD_SHUTDOWN}) + "\n")
        proc.stdin.flush()
        shutdown_payload = json.loads(proc.stdout.readline())
        assert shutdown_payload["result"]["shutdown"] == "accepted"
    finally:
        proc.wait(timeout=5)

    assert proc.returncode == 0

    (root / "src" / "ops.py").write_text(
        "class OperatorGraph:\n    pass\n",
        encoding="utf-8",
    )
    refreshed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "workspace-refresh",
            str(workspace),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    refreshed_payload = json.loads(refreshed.stdout)
    assert "src/ops.py" in refreshed_payload["operation"]["changed_paths"]
