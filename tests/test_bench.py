from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.bench import benchmark_root, render_markdown_benchmark


def _medium_repo() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "medium_repo"


def test_benchmark_root_returns_expected_measurements() -> None:
    report = benchmark_root(
        _medium_repo(),
        namespace="medium",
        query_text="RuntimeGraph",
    )

    measurement_names = [item.name for item in report.measurements]

    assert report.namespace == "medium"
    assert report.node_count >= 12
    assert report.edge_count >= 12
    assert report.snapshot_bytes > 0
    assert measurement_names == [
        "index",
        "snapshot_serialize",
        "query",
        "report",
        "export_dot",
        "export_mermaid",
        "graphify_export",
    ]
    assert all(item.duration_ms >= 0.0 for item in report.measurements)


def test_benchmark_markdown_renders_sections() -> None:
    report = benchmark_root(
        _medium_repo(),
        namespace="medium",
        query_text="RuntimeGraph",
    )

    markdown = render_markdown_benchmark(report)

    assert "# PragmaGraph Benchmark Report" in markdown
    assert "## Measurements" in markdown
    assert "`graphify_export`" in markdown


def test_cli_benchmark_emits_json_and_markdown() -> None:
    root = _medium_repo()

    markdown = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "benchmark",
            str(root),
            "--namespace",
            "medium",
            "--query",
            "RuntimeGraph",
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
                "benchmark",
                str(root),
                "--namespace",
                "medium",
                "--query",
                "RuntimeGraph",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    assert "# PragmaGraph Benchmark Report" in markdown
    assert payload["namespace"] == "medium"
    assert payload["node_count"] >= 12
    assert payload["measurements"][0]["name"] == "index"
