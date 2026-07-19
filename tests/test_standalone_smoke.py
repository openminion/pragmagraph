from __future__ import annotations

import json
import subprocess
import sys
from threading import Thread
import tomllib
from urllib.request import urlopen

import pytest


def test_python_m_pragmagraph_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pragmagraph", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "git_identity_mode_default": "name_email_hash",
        "openminion_imports": False,
        "package": "pragmagraph",
        "semantic_contract": True,
        "stable_import_roots": [
            "pragmagraph",
            "pragmagraph.contracts",
            "pragmagraph.models",
            "pragmagraph.query",
            "pragmagraph.storage",
            "pragmagraph.adapters",
            "pragmagraph.bench",
            "pragmagraph.portability",
            "pragmagraph.parsers",
            "pragmagraph.export",
            "pragmagraph.evidence",
            "pragmagraph.graphify",
            "pragmagraph.report",
            "pragmagraph.refresh",
            "pragmagraph.operations",
            "pragmagraph.security",
            "pragmagraph.service",
            "pragmagraph.ui",
            "pragmagraph.workspace",
            "pragmagraph.navigation",
            "pragmagraph.interchange",
            "pragmagraph.topology",
            "pragmagraph.docgraph",
            "pragmagraph.planner",
            "pragmagraph.certification",
            "pragmagraph.lineage",
            "pragmagraph.parser_support",
            "pragmagraph.viewer",
        ],
        "status": "semantic-alpha",
        "version": "0.0.6",
    }


def test_console_script_contract_and_release_smoke_shape() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    release_check = (root / "scripts" / "release_check.py").read_text()

    assert pyproject["project"]["scripts"]["pragmagraph-smoke"] == (
        "pragmagraph.__main__:main"
    )
    assert pyproject["project"]["scripts"]["pragmagraph-ui"] == (
        "pragmagraph.__main__:ui_preview_main"
    )
    assert pyproject["project"]["scripts"]["pragmagraph-server"] == (
        "pragmagraph.server.__main__:main"
    )
    assert "twine" in release_check
    assert "pragmagraph-smoke" in release_check
    assert "pragmagraph-ui" in release_check
    assert "pragmagraph-server" in release_check
    assert "pragmagraph-artifact.json" in release_check
    assert "pragmagraph-report.json" in release_check
    assert "pragmagraph-report.md" in release_check
    assert "graphfakos-ui" in release_check
    assert "semantic_contract" in release_check
    assert "semantic alpha" in release_check


def test_python_m_pragmagraph_ui_preview_writes_html(tmp_path) -> None:
    output_path = tmp_path / "pragmagraph-ui.html"
    artifact_path = tmp_path / "pragmagraph-artifact.json"
    embed_path = tmp_path / "pragmagraph-embed.html"
    report_path = tmp_path / "pragmagraph-report.json"
    markdown_path = tmp_path / "pragmagraph-report.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "ui-preview",
            "--screen",
            "provider_status",
            "--html-out",
            str(output_path),
            "--artifact-out",
            str(artifact_path),
            "--embed-out",
            str(embed_path),
            "--report-out",
            str(report_path),
            "--markdown-report-out",
            str(markdown_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    html = output_path.read_text(encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert payload["output_path"] == str(output_path)
    assert payload["screen"] == "provider_status"
    assert payload["node_count"] == 4
    assert payload["artifact"]["artifact"] is True
    assert payload["embed"]["embedded"] is True
    assert payload["report"]["report"] is True
    assert payload["markdown_report"]["markdown_report"] is True
    assert "GraphFakos" in html
    assert "PragmaGraph" in html
    assert "Provider Status" in html
    assert "PragmaGraph Observed Source Graph" in html
    assert "data-graphfakos-embed='true'" in embed_path.read_text(encoding="utf-8")
    assert report["graph"]["provider_label"] == "PragmaGraph"
    assert artifact["provider_id"] == "pragmagraph"
    assert "# GraphFakos Report" in markdown_path.read_text(encoding="utf-8")


def test_pragmagraph_ui_preview_server_serves_visual_routes() -> None:
    from pragmagraph.ui import UiPreviewRequest, make_ui_preview_server

    try:
        server = make_ui_preview_server(
            UiPreviewRequest(screen="search", query="RuntimeGraph"),
            port=0,
        )
    except PermissionError:
        pytest.skip("local socket binding is unavailable in this sandbox")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(server.preview_url, timeout=5) as response:
            search_html = response.read().decode("utf-8")
        graph_url = server.preview_url.rsplit("/", 1)[0] + "/provider_status"
        with urlopen(graph_url, timeout=5) as response:
            status_html = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert "Graph Canvas" in search_html
    assert "PragmaGraph Observed Source Graph" in search_html
    assert "href='/provider_status" in search_html
    assert "Provider Status" in status_html
