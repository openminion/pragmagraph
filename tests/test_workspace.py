from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pragmagraph.models import PragmaGraphError, QueryRequest
from pragmagraph.query import query
from pragmagraph.service import (
    LocalQueryService,
    METHOD_QUERY,
    METHOD_REFRESH,
    METHOD_SHUTDOWN,
    ServiceRequest,
)
from pragmagraph.workspace import (
    load_workspace_config,
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


def _run_workspace_cli(*args: object) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "pragmagraph", *(str(arg) for arg in args), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


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
    assert Path(result.workspace.paths.cache_path).is_file()
    assert result.operation.status.status == "fresh"

    status = load_workspace_status(workspace)
    assert status.workspace.label == "demo"
    assert status.workspace.namespace == "fixture"
    assert status.snapshot_present is True
    assert status.manifest_present is True
    assert status.profile_present is True
    assert status.cache_present is True
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

    init_payload = _run_workspace_cli(
        "workspace-init",
        root,
        "--workspace",
        workspace,
        "--label",
        "demo",
        "--namespace",
        "fixture",
    )
    assert init_payload["workspace"]["label"] == "demo"

    status_payload = _run_workspace_cli("workspace-status", workspace)
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
    refreshed_payload = _run_workspace_cli("workspace-refresh", workspace)
    assert "src/ops.py" in refreshed_payload["operation"]["changed_paths"]
    assert refreshed_payload["operation"]["work"]["parsed_path_count"] == 1


def test_cli_workspace_config_and_demo_ui_flow(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    config_path = tmp_path / "workspace.toml"
    workspace = tmp_path / "workspace"
    html_path = tmp_path / "demo.html"
    artifact_path = tmp_path / "demo-artifact.json"

    config_payload = _run_workspace_cli(
        "workspace-config-init",
        root,
        "--out",
        config_path,
        "--workspace",
        workspace,
        "--label",
        "demo",
        "--namespace",
        "fixture",
        "--ui-screen",
        "provider_status",
        "--ui-query",
        "RuntimeGraph",
    )
    status_payload = _run_workspace_cli("workspace-config-status", config_path)
    demo_payload = _run_workspace_cli(
        "demo-ui",
        "--config",
        config_path,
        "--html-out",
        html_path,
        "--artifact-out",
        artifact_path,
    )

    config = load_workspace_config(config_path)
    assert config_payload["config"]["label"] == "demo"
    assert config.label == "demo"
    assert status_payload["workspace_status"] is None
    assert demo_payload["screen"] == "provider_status"
    assert demo_payload["node_count"] >= 1
    assert (workspace / "workspace.json").is_file()
    assert "PragmaGraph" in html_path.read_text(encoding="utf-8")
    assert json.loads(artifact_path.read_text(encoding="utf-8"))["provider_id"] == (
        "pragmagraph"
    )


def test_workspace_config_rejects_schema_drift_and_escapes_toml(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "workspace.toml"
    config_path.write_text(
        "\n".join(
            [
                'schema_version = "unsupported"',
                'label = "demo"',
                'namespace = "default"',
                'root_path = "."',
                'workspace_path = ".pragmagraph/workspace"',
                'git_identity_mode = "name_email_hash"',
                'store_path = "graph.sqlite"',
                "",
                "[ui]",
                'screen = "search"',
                'query = "RuntimeGraph"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(PragmaGraphError, match="schema_version"):
        load_workspace_config(config_path)

    escaped_path = tmp_path / "escaped.toml"
    save_payload = _run_workspace_cli(
        "workspace-config-init",
        ".",
        "--out",
        escaped_path,
        "--label",
        "line\nbreak",
    )

    loaded = load_workspace_config(escaped_path)
    assert save_payload["config"]["label"] == "line\nbreak"
    assert loaded.label == "line\nbreak"
