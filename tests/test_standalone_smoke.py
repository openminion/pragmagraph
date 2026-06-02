from __future__ import annotations

import json
import subprocess
import sys
import tomllib


def test_python_m_pragmagraph_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pragmagraph", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload == {
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
            "pragmagraph.portability",
            "pragmagraph.parsers",
            "pragmagraph.export",
            "pragmagraph.graphify",
            "pragmagraph.report",
            "pragmagraph.refresh",
            "pragmagraph.security",
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
    assert "twine" in release_check
    assert "pragmagraph-smoke" in release_check
    assert "semantic_contract" in release_check
    assert "semantic alpha" in release_check
