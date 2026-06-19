from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.report import build_report, render_markdown_report
from pragmagraph.storage import save_snapshot
from .package_paths import build_fixture_repo


def _report_fixture_root(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        repo_name="report-repo",
        files={
            "README.md": "# Demo\n\nSee [Guide](docs/guide.md#Install).\n",
            "docs/guide.md": "# Guide\n\n## Install\n\nSee [Missing](missing.md#Nope).\n",
            "pyproject.toml": '[project]\nname = "demo"\ndependencies = ["ruff"]\n',
            "src/app.py": (
                "from helper import make_value\n\n"
                "class RuntimeGraph:\n"
                "    def build(self):\n"
                "        return make_value()\n"
            ),
            "src/helper.py": "def make_value():\n    return True\n",
        },
    )


def test_build_report_returns_structural_summary(tmp_path: Path) -> None:
    snapshot = index_path(_report_fixture_root(tmp_path), namespace="fixture")

    report = build_report(snapshot, top_n=5)

    assert report.summary.namespace == "fixture"
    assert report.summary.node_count == len(snapshot.nodes)
    assert report.summary.edge_count == len(snapshot.edges)
    assert report.summary.dependency_count >= 1
    assert report.summary.config_count >= 1
    assert report.summary.node_kinds["python_class"] >= 1
    assert report.summary.edge_kinds["depends_on"] >= 1
    assert report.dependencies[0].dependency == "ruff"
    assert report.hotspots
    assert any(
        item.category == "unresolved_markdown_reference"
        for item in report.unresolved_items
    )
    assert report.structural_summary
    assert report.suggested_queries


def test_markdown_report_renders_expected_sections(tmp_path: Path) -> None:
    snapshot = index_path(_report_fixture_root(tmp_path), namespace="fixture")

    markdown = render_markdown_report(build_report(snapshot))

    assert "# PragmaGraph Structural Report" in markdown
    assert "## Hotspots" in markdown
    assert "## Dependencies" in markdown
    assert "## Structural Summary" in markdown
    assert "`ruff` declared by `pyproject.toml`" in markdown


def test_cli_report_emits_json_and_markdown(tmp_path: Path) -> None:
    snapshot = index_path(_report_fixture_root(tmp_path), namespace="fixture")
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, snapshot_path)

    markdown = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "report",
            str(snapshot_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "report",
                str(snapshot_path),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    assert "# PragmaGraph Structural Report" in markdown
    assert payload["summary"]["namespace"] == "fixture"
    assert payload["dependencies"][0]["dependency"] == "ruff"
    assert payload["hotspots"]
