from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.bench import (
    benchmark_generated_scale,
    benchmark_root,
    render_markdown_benchmark,
)

from .package_paths import fixture_repo


def _medium_repo() -> Path:
    return fixture_repo("medium_repo")


def test_benchmark_root_returns_expected_measurements() -> None:
    report = benchmark_root(
        _medium_repo(),
        namespace="medium",
        query_text="RuntimeGraph",
    )

    measurement_names = [item.name for item in report.measurements]

    assert report.namespace == "medium"
    assert report.fixture_profile == "medium"
    assert report.node_count >= 12
    assert report.edge_count >= 12
    assert report.snapshot_bytes > 0
    assert measurement_names == [
        "index",
        "snapshot_serialize",
        "refresh_unchanged",
        "json_query",
        "sqlite_import",
        "sqlite_query",
        "report",
        "export_dot",
        "export_mermaid",
        "graphify_export",
    ]
    assert report.omitted_count >= 0
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
    assert "`refresh_unchanged`" in markdown
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
    assert payload["fixture_profile"] == "medium"
    assert payload["measurements"][0]["name"] == "index"


def test_generated_scale_profiles_report_deterministic_bounded_work() -> None:
    small = benchmark_generated_scale(1_000)
    medium = benchmark_generated_scale(10_000)

    for evidence, expected in ((small, 1_000), (medium, 10_000)):
        assert evidence.node_count == expected
        assert evidence.edge_count == expected - 1
        assert evidence.query_strategy in {"direct_exact", "indexed_trigram"}
        assert evidence.query_rows_examined < expected
        assert evidence.traversal_rows_examined < expected
        assert evidence.snapshot_deserialized is False
        assert evidence.normalized_rows_written == 0
        assert evidence.snapshot_payload_bytes_written == evidence.snapshot_bytes
