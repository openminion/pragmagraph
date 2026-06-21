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
        ],
        "status": "semantic-alpha",
        "version": "0.0.1",
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
    assert "twine" in release_check
    assert "pragmagraph-smoke" in release_check
    assert "pragmagraph-ui" in release_check
    assert "semantic_contract" in release_check
    assert "semantic alpha" in release_check


def test_python_m_pragmagraph_ui_preview_writes_html(tmp_path) -> None:
    output_path = tmp_path / "pragmagraph-ui.html"
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
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["output_path"] == str(output_path)
    assert payload["screen"] == "provider_status"
    assert payload["node_count"] == 4
    assert "PragmaGraph" in output_path.read_text(encoding="utf-8")


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

    assert "Ranked Results" in search_html
    assert "href='/provider_status'" in search_html
    assert "Provider Status" in status_html
