from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures" / "repos"
CONTRACT_ROOT = PACKAGE_ROOT / "tests" / "contracts"


def fixture_repo(name: str) -> Path:
    return FIXTURE_ROOT / name


def contract_path(name: str) -> Path:
    return CONTRACT_ROOT / name
