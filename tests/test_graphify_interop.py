from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.graphify import (
    GRAPHIFY_INTEROP_FORMAT,
    snapshot_from_graphify_payload,
    to_graphify_payload,
)
from pragmagraph.storage import load_snapshot, save_snapshot


def _graphify_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "graphify-repo"
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# Demo\n\nSee [App](src/app.py).\n")
    (root / "src" / "app.py").write_text(
        "from helper import make_value\n\ndef run():\n    return make_value()\n",
        encoding="utf-8",
    )
    (root / "src" / "helper.py").write_text(
        "def make_value():\n    return 42\n",
        encoding="utf-8",
    )
    return root


def test_graphify_payload_is_deterministic_subset(tmp_path: Path) -> None:
    snapshot = index_path(_graphify_fixture_root(tmp_path), namespace="fixture")

    payload = to_graphify_payload(snapshot)

    assert payload["format"] == GRAPHIFY_INTEROP_FORMAT
    assert payload["source"]["namespace"] == "fixture"
    assert [node["id"] for node in payload["nodes"]] == sorted(
        node.id for node in snapshot.nodes
    )
    assert [edge["id"] for edge in payload["edges"]] == sorted(
        edge.id for edge in snapshot.edges
    )
    assert payload["nodes"][0]["properties"]["source_ref"]


def test_graphify_payload_round_trips_supported_subset(tmp_path: Path) -> None:
    snapshot = index_path(_graphify_fixture_root(tmp_path), namespace="fixture")
    payload = to_graphify_payload(snapshot)

    imported = snapshot_from_graphify_payload(payload)

    assert imported.namespace == snapshot.namespace
    assert imported.root_path == snapshot.root_path
    assert {node.id for node in imported.nodes} == {node.id for node in snapshot.nodes}
    assert {edge.id for edge in imported.edges} == {edge.id for edge in snapshot.edges}


def test_cli_graphify_export_and_import(tmp_path: Path) -> None:
    snapshot = index_path(_graphify_fixture_root(tmp_path), namespace="fixture")
    snapshot_path = tmp_path / "snapshot.json"
    payload_path = tmp_path / "graphify.json"
    imported_path = tmp_path / "imported.json"
    save_snapshot(snapshot, snapshot_path)

    export_stdout = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "graphify-export",
            str(snapshot_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    payload_path.write_text(export_stdout, encoding="utf-8")

    import_stdout = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "graphify-import",
            str(payload_path),
            "--out",
            str(imported_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    payload = json.loads(export_stdout)
    health = json.loads(import_stdout)
    imported = load_snapshot(imported_path)

    assert payload["format"] == GRAPHIFY_INTEROP_FORMAT
    assert health["ok"] is True
    assert len(imported.nodes) == len(snapshot.nodes)
