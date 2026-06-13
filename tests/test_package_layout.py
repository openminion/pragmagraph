from __future__ import annotations

from pathlib import Path


def test_root_layout_stays_clean_and_intentional() -> None:
    root = Path(__file__).resolve().parents[1]

    assert (root / "docs" / "README.md").is_file()
    assert (root / "docs" / "reference").is_dir()
    assert (root / "src" / "pragmagraph" / "README.md").is_file()
    assert (root / "tests" / "fixtures" / "repos").is_dir()
    assert (root / "tests" / "contracts").is_dir()

    assert not (root / "fixtures").exists()
    assert not (root / "handoff").exists()
    assert not (root / "docs" / "public-package-readme-template.md").exists()


def test_docs_reference_surface_contains_expected_package_refs() -> None:
    root = Path(__file__).resolve().parents[1] / "docs" / "reference"

    expected = {
        "benchmarking.md",
        "certification-readiness-matrix.md",
        "export-mode.md",
        "git-history-mode.md",
        "graphify-interop.md",
        "report-mode.md",
        "service-mode.md",
        "ui-contracts.md",
        "workspace-mode.md",
    }

    assert expected.issubset({path.name for path in root.iterdir() if path.is_file()})
