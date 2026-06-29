from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.navigation import build_repo_map, render_compact_handoff
from pragmagraph.storage import save_snapshot

from .package_paths import build_fixture_repo


def _repo_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        files={
            "README.md": "# Demo\n\n## Install\n\nSee src/app.py.\n",
            "src/app.py": "class RuntimeGraph:\n    pass\n",
            "src/index.ts": "export const makeRuntimeGraph = () => true;\n",
        },
    )


def test_repo_map_summarizes_navigation_sections(tmp_path: Path) -> None:
    snapshot = index_path(_repo_root(tmp_path), namespace="fixture")

    repo_map = build_repo_map(snapshot, top_n=4)
    payload = repo_map.to_dict()

    assert payload["namespace"] == "fixture"
    assert payload["stats"]["node_count"] == len(snapshot.nodes)
    assert any(section.title == "Files" for section in repo_map.sections)
    assert any(
        "RuntimeGraph" in item
        for section in repo_map.sections
        if section.title == "Symbols"
        for item in section.items
    )
    handoff = render_compact_handoff(snapshot, top_n=3)
    assert "observed facts" in handoff
    assert "PragmaGraph Compact Handoff" in handoff


def test_cli_repo_map_outputs_json_and_handoff_markdown(tmp_path: Path) -> None:
    snapshot = index_path(_repo_root(tmp_path), namespace="fixture")
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, snapshot_path)

    json_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "repo-map",
            str(snapshot_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(json_result.stdout)
    assert payload["stats"]["node_count"] == len(snapshot.nodes)

    handoff_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "repo-map",
            str(snapshot_path),
            "--handoff",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "PragmaGraph Compact Handoff" in handoff_result.stdout
