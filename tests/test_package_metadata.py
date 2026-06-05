from __future__ import annotations

from pathlib import Path
import tomllib


def test_package_release_artifacts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "LICENSE").is_file()
    assert (root / "NOTICE").is_file()
    assert (root / "RELEASING.md").is_file()
    assert (root / "pyproject.toml").is_file()
    assert (root / "MANIFEST.in").is_file()


def test_package_readme_mentions_release_runbook() -> None:
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()
    assert "RELEASING.md" in readme
    assert "Apache-2.0" in readme


def test_package_policy_and_release_automation_docs_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "API_COMPATIBILITY.md").is_file()
    assert (root / "scripts" / "release_check.py").is_file()
    assert (root / "examples" / "basic_usage.py").is_file()
    assert (root / "docs" / "README.md").is_file()
    assert (root / "docs" / "reference" / "report-mode.md").is_file()
    assert (root / "docs" / "reference" / "export-mode.md").is_file()
    assert (root / "docs" / "reference" / "benchmarking.md").is_file()
    assert (root / "docs" / "reference" / "graphify-interop.md").is_file()
    assert (root / "docs" / "reference" / "service-mode.md").is_file()
    assert (root / "docs" / "reference" / "ui-contracts.md").is_file()
    assert (root / "docs" / "reference" / "certification-readiness-matrix.md").is_file()
    assert (root / "tests" / "fixtures" / "repos" / "tiny_repo").is_dir()
    assert (root / "tests" / "contracts" / "capabilities.json").is_file()
    assert not (root / "fixtures").exists()
    assert not (root / "handoff").exists()


def test_package_readme_mentions_policy_and_quickstart() -> None:
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()
    assert "API_COMPATIBILITY.md" in readme
    assert "External Consumer Quickstart" in readme
    assert "pragmagraph index" in readme
    assert "pragmagraph report" in readme
    assert "pragmagraph export" in readme
    assert "pragmagraph benchmark" in readme
    assert "pragmagraph graphify-export" in readme
    assert "pragmagraph serve" in readme
    assert "pragmagraph.ui" in readme


def test_package_metadata_declares_public_urls() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    )

    assert pyproject["project"]["urls"] == {
        "Repository": "https://github.com/openminion/pragmagraph",
        "Download": "https://pypi.org/project/pragmagraph/",
    }
