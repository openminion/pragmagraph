from __future__ import annotations

from pathlib import Path


def test_release_check_is_package_local() -> None:
    release_check = (
        Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"
    ).read_text()

    assert "pragmagraph" in release_check
    assert "sophiagraph" not in release_check
    assert "openminion" not in release_check.lower()
    assert "pytest" in release_check
    assert "build" in release_check
    assert "pragmagraph.service" in release_check
    assert "pragmagraph.ui" in release_check
