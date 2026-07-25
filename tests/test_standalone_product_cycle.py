from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.portability import inspect_graph_pack
from pragmagraph.storage import SQLiteGraphStore, load_snapshot, save_snapshot
from pragmagraph.ui import UiPreviewRequest, build_delta_review_payload

from .package_paths import build_fixture_repo


def _repo(tmp_path: Path, *, extra: str = "") -> Path:
    return build_fixture_repo(
        tmp_path,
        repo_name="product-cycle-repo",
        files={
            "README.md": "# Product Cycle\n\nSee `src/app.py`.\n",
            "src/app.py": f"class RuntimeGraph:\n    pass\n{extra}",
        },
    )


def _run_cli_json(*args: object) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-m", "pragmagraph", *(str(arg) for arg in args), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_workbench_writes_static_html_artifact_and_store_from_root(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    workspace = tmp_path / "workspace"
    html_path = tmp_path / "workbench.html"
    artifact_path = tmp_path / "workbench-artifact.json"

    payload = _run_cli_json(
        "workbench",
        "--root",
        root,
        "--workspace",
        workspace,
        "--screen",
        "evidence",
        "--html-out",
        html_path,
        "--artifact-out",
        artifact_path,
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["screen"] == "evidence"
    assert payload["node_count"] >= 1
    assert (workspace / "workspace.json").is_file()
    assert (workspace / "graph.sqlite").is_file()
    assert "PragmaGraph" in html_path.read_text(encoding="utf-8")
    assert artifact["provider_payload"]["evidence_workbench"]["boundary"] == (
        "observed_facts_only"
    )


def test_delta_review_payload_and_ui_screen_compare_snapshots(tmp_path: Path) -> None:
    before = index_path(_repo(tmp_path), namespace="delta")
    after = index_path(
        _repo(tmp_path, extra="\nclass OperatorGraph:\n    pass\n"),
        namespace="delta",
    )
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    artifact_path = tmp_path / "delta-artifact.json"
    save_snapshot(before, before_path)
    save_snapshot(after, after_path)

    request = UiPreviewRequest(
        screen="delta_review",
        snapshot=str(after_path),
        before_snapshot=str(before_path),
        after_snapshot=str(after_path),
    )
    payload = build_delta_review_payload(after, request)
    ui_payload = _run_cli_json(
        "ui-preview",
        "--screen",
        "delta_review",
        "--snapshot",
        after_path,
        "--before-snapshot",
        before_path,
        "--after-snapshot",
        after_path,
        "--artifact-out",
        artifact_path,
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "snapshot_compare"
    assert payload["delta"]["has_changes"] is True
    assert ui_payload["delta_review"]["delta"]["has_changes"] is True
    assert artifact["provider_payload"]["delta_review"]["boundary"] == (
        "observed_facts_only"
    )


def test_graph_pack_exports_imports_snapshot_and_materialized_store(
    tmp_path: Path,
) -> None:
    snapshot = index_path(_repo(tmp_path), namespace="pack")
    snapshot_path = tmp_path / "snapshot.json"
    pack_dir = tmp_path / "graph-pack"
    imported_snapshot = tmp_path / "imported.json"
    imported_store = tmp_path / "imported.sqlite"
    save_snapshot(snapshot, snapshot_path)

    export_payload = _run_cli_json(
        "graph-pack-export",
        snapshot_path,
        pack_dir,
        "--include-store",
    )
    inspect_payload = _run_cli_json("graph-pack-inspect", pack_dir)
    import_payload = _run_cli_json(
        "graph-pack-import",
        pack_dir,
        "--snapshot-out",
        imported_snapshot,
        "--store-out",
        imported_store,
    )

    manifest = inspect_graph_pack(pack_dir)
    assert export_payload["manifest"]["includes_store"] is True
    assert inspect_payload["schema_version"] == "pragmagraph.graph_pack.v1alpha1"
    assert manifest.namespace == "pack"
    assert load_snapshot(imported_snapshot).namespace == "pack"
    assert SQLiteGraphStore(imported_store).manifest().namespace == "pack"
    assert import_payload["manifest"]["includes_store"] is True


def test_storage_backend_catalog_and_mcp_config_are_public_cli_surfaces(
    tmp_path: Path,
) -> None:
    snapshot = index_path(_repo(tmp_path), namespace="cycle")
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, snapshot_path)

    backends = _run_cli_json("store-backends")
    selected = _run_cli_json(
        "store-backends", "--backend", "json", "--path", snapshot_path
    )
    mcp = _run_cli_json("mcp-config", "--snapshot", snapshot_path)

    entries = {entry["backend"]: entry for entry in backends["entries"]}
    assert entries["json"]["canonical"] is True
    assert entries["sqlite"]["materialized"] is True
    assert entries["vector_sidecar"]["status"] == "boundary_reserve"
    assert selected["selected"]["backend"] == "json"
    assert mcp["transport"] == "stdio"
    assert mcp["clients"][0]["config"]["mcpServers"]["pragmagraph"]["command"] == (
        "pragmagraph-server"
    )
