from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _quality_module() -> ModuleType:
    path = REPO_ROOT / "scripts" / "validate_quality_patterns.py"
    spec = importlib.util.spec_from_file_location("pragmagraph_quality_patterns", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_quality_pattern_validator_passes_current_baselines() -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_quality_patterns.py"),
            "--check",
            "all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_git_python_files_follow_the_live_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = tmp_path / "tracked.py"
    tracked.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.py"], check=True)
    tracked.unlink()
    untracked = tmp_path / "untracked.py"
    untracked.write_text("VALUE = 2\n", encoding="utf-8")

    quality = _quality_module()
    monkeypatch.setattr(quality, "REPO_ROOT", tmp_path)

    assert quality._git_python_files() == [untracked]
