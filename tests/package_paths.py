from __future__ import annotations

from pathlib import Path
from typing import Mapping


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures" / "repos"
CONTRACT_ROOT = PACKAGE_ROOT / "tests" / "contracts"


def fixture_repo(name: str) -> Path:
    return FIXTURE_ROOT / name


def contract_path(name: str) -> Path:
    return CONTRACT_ROOT / name


def build_fixture_repo(
    tmp_path: Path,
    *,
    repo_name: str = "repo",
    files: Mapping[str, str],
) -> Path:
    root = tmp_path / repo_name
    for relative_path, contents in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")
    return root
