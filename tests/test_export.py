from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.export import render_dot, render_graph_export, render_mermaid
from pragmagraph.storage import save_snapshot
from .package_paths import build_fixture_repo


def _export_fixture_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        repo_name="export-repo",
        files={
            "README.md": "# Demo\n\nSee [App](src/app.py).\n",
            "src/app.py": (
                "from helper import make_value\n\ndef run():\n    return make_value()\n"
            ),
            "src/helper.py": "def make_value():\n    return 42\n",
        },
    )


def test_render_dot_is_deterministic_graph_text(tmp_path: Path) -> None:
    snapshot = index_path(_export_fixture_root(tmp_path), namespace="fixture")

    first = render_dot(snapshot)
    second = render_graph_export(snapshot, format="dot")

    assert first == second
    assert first.startswith("// export_schema_version=")
    assert "digraph pragmagraph {\n" in first
    assert "rankdir=LR" in first
    assert "->" in first
    assert 'label="contains"' in first
    assert "src/app.py" in first


def test_render_mermaid_is_deterministic_graph_text(tmp_path: Path) -> None:
    snapshot = index_path(_export_fixture_root(tmp_path), namespace="fixture")

    first = render_mermaid(snapshot)
    second = render_graph_export(snapshot, format="mermaid")

    assert first == second
    assert first.startswith("%% export_schema_version=")
    assert "flowchart LR\n" in first
    assert "-->|contains|" in first
    assert "src/app.py" in first


def test_cli_export_emits_dot_and_mermaid(tmp_path: Path) -> None:
    snapshot = index_path(_export_fixture_root(tmp_path), namespace="fixture")
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, snapshot_path)

    dot = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "export",
            str(snapshot_path),
            "--format",
            "dot",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    mermaid = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "export",
            str(snapshot_path),
            "--format",
            "mermaid",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert dot.startswith("// export_schema_version=")
    assert mermaid.startswith("%% export_schema_version=")
