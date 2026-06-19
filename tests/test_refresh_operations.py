from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.operations import (
    build_refresh_plan,
    build_refresh_profile,
    load_refresh_profile,
    load_refresh_status,
    run_refresh_profile,
)
from pragmagraph.refresh import build_manifest
from pragmagraph.service import LocalQueryService, METHOD_REFRESH, ServiceRequest
from .package_paths import build_fixture_repo


def _repo_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        files={
            "README.md": "# Demo\n",
            "src/app.py": "class RuntimeGraph:\n    pass\n",
        },
    )


def test_build_refresh_plan_surfaces_changed_and_removed_paths(
    tmp_path: Path,
) -> None:
    root = _repo_root(tmp_path)
    initial = build_refresh_plan(root, namespace="fixture")
    previous_manifest = build_manifest(root)

    (root / "src" / "app.py").write_text(
        "class RuntimeGraph:\n    pass\n\nclass Worker:\n    pass\n",
        encoding="utf-8",
    )
    (root / "README.md").unlink()
    (root / "src" / "extra.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    updated = build_refresh_plan(
        root,
        namespace="fixture",
        previous_manifest=previous_manifest,
    )

    # The first plan is still useful as a baseline sanity check.
    assert initial.manifest_entry_count == 2
    assert "README.md" in updated.changed_paths
    assert "src/app.py" in updated.changed_paths
    assert "src/extra.py" in updated.changed_paths
    assert "README.md" in updated.removed_paths
    assert any(item.status == "removed" for item in updated.path_changes)


def test_profile_run_persists_snapshot_manifest_and_status(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    profile = build_refresh_profile(
        label="demo",
        root_path=root,
        snapshot_path=tmp_path / "snapshot.json",
        manifest_path=tmp_path / "manifest.json",
        state_path=tmp_path / "status.json",
        namespace="fixture",
    )

    operation = run_refresh_profile(profile)

    assert Path(profile.snapshot_path).is_file()
    assert Path(profile.manifest_path).is_file()
    assert Path(profile.state_path).is_file()
    assert operation.status.status == "fresh"
    assert operation.status.snapshot_id
    assert operation.status.manifest_entry_count == 2
    status = load_refresh_status(profile.state_path)
    assert status.status == "fresh"
    assert status.namespace == "fixture"
    profile_path = _save_profile_fixture(profile, tmp_path / "profile.json")
    loaded_profile = load_refresh_profile(profile_path)
    assert loaded_profile.root_path == str(root.resolve())


def _save_profile_fixture(profile, path: Path) -> Path:
    path.write_text(json.dumps(profile.to_dict(), sort_keys=True), encoding="utf-8")
    return path


def test_cli_profile_init_run_and_status_commands(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    profile_path = tmp_path / "profile.json"
    snapshot_path = tmp_path / "snapshot.json"
    manifest_path = tmp_path / "manifest.json"
    state_path = tmp_path / "status.json"

    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "profile-init",
            str(root),
            "--out",
            str(profile_path),
            "--label",
            "demo",
            "--namespace",
            "fixture",
            "--snapshot-out",
            str(snapshot_path),
            "--manifest-out",
            str(manifest_path),
            "--state-out",
            str(state_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    init_payload = json.loads(init.stdout)
    assert init_payload["label"] == "demo"
    assert profile_path.is_file()

    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "profile-run",
            str(profile_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    run_payload = json.loads(run.stdout)
    assert run_payload["status"]["status"] == "fresh"

    status = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "refresh-status",
            str(state_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status_payload = json.loads(status.stdout)
    assert status_payload["status"] == "fresh"
    assert status_payload["manifest_entry_count"] == 2


def test_root_service_health_and_refresh_return_refresh_state(tmp_path: Path) -> None:
    root = _repo_root(tmp_path)
    state_out = tmp_path / "service-status.json"
    service = LocalQueryService.from_root(
        root,
        namespace="fixture",
        snapshot_out_path=tmp_path / "service-snapshot.json",
        manifest_out_path=tmp_path / "service-manifest.json",
        state_out_path=state_out,
    )

    health_payload = service.handle_request(
        ServiceRequest(id="health", method="health", params={})
    )[0].to_dict()["result"]
    assert health_payload["service"]["refresh_state"]["status"] == "fresh"
    assert state_out.is_file()

    (root / "src" / "ops.py").write_text(
        "class OperatorGraph:\n    pass\n", encoding="utf-8"
    )
    refreshed = service.handle_request(
        ServiceRequest(id="refresh", method=METHOD_REFRESH, params={})
    )[0].to_dict()["result"]

    assert refreshed["refresh_state"]["status"] == "fresh"
    assert refreshed["refresh_state"]["changed_path_count"] >= 1
