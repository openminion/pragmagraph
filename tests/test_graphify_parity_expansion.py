from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.contracts import (
    EDGE_CALLS,
    EDGE_DEPENDS_ON,
    EDGE_INHERITS,
    EDGE_REFERENCES_DOC,
    NODE_CONFIG,
    NODE_IMPORT,
    NODE_PYTHON_CLASS,
    NODE_PYTHON_METHOD,
)
from pragmagraph.models import QueryRequest
from pragmagraph.query import query
from pragmagraph.refresh import refresh_snapshot
from pragmagraph.security import ScopePolicy

from .package_paths import contract_path, fixture_repo


def _mixed_repo(tmp_path: Path) -> Path:
    root = tmp_path / "mixed"
    (root / "src").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / ".gitignore").write_text("ignored.md\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# Project\n\nSee [Usage](#usage) and [[docs/guide.md#Install]].\n\n## Usage\n",
        encoding="utf-8",
    )
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\n## Install\n\nBack to [missing](missing.md#Nope).\n",
        encoding="utf-8",
    )
    (root / "ignored.md").write_text("# Ignored\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["ruff"]\n',
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps({"dependencies": {"left-pad": "1.0.0"}}),
        encoding="utf-8",
    )
    (root / "src" / "app.py").write_text(
        "import json\n"
        "import missing.module\n"
        "from helper import make_value\n\n"
        "class Base:\n"
        "    pass\n\n"
        "class RuntimeGraph(Base):\n"
        "    def build(self):\n"
        "        return json.dumps({'ok': make_value()})\n",
        encoding="utf-8",
    )
    (root / "src" / "helper.py").write_text(
        "def make_value():\n    return True\n",
        encoding="utf-8",
    )
    return root


def test_expanded_indexer_extracts_python_markdown_and_config_facts(
    tmp_path: Path,
) -> None:
    snapshot = index_path(_mixed_repo(tmp_path), namespace="fixture")

    assert any(
        node.kind == NODE_PYTHON_CLASS and node.label == "RuntimeGraph"
        for node in snapshot.nodes
    )
    assert any(
        node.kind == NODE_PYTHON_METHOD and node.label == "build"
        for node in snapshot.nodes
    )
    assert any(
        node.kind == NODE_IMPORT and node.label == "json" for node in snapshot.nodes
    )
    assert any(
        node.kind == NODE_CONFIG and node.label == "pyproject.toml"
        for node in snapshot.nodes
    )
    assert any(edge.kind == EDGE_INHERITS for edge in snapshot.edges)
    assert any(edge.kind == EDGE_CALLS for edge in snapshot.edges)
    assert any(
        edge.kind == "imports" and edge.metadata.get("resolved")
        for edge in snapshot.edges
    )
    assert any(edge.kind == EDGE_DEPENDS_ON for edge in snapshot.edges)
    assert any(edge.kind == EDGE_REFERENCES_DOC for edge in snapshot.edges)
    assert any(
        item.reason == "gitignored" and item.item_id == "ignored.md"
        for item in snapshot.omitted
    )
    assert any(
        item.reason == "unresolved_markdown_reference" for item in snapshot.omitted
    )
    assert any(item.reason == "unresolved_local_import" for item in snapshot.omitted)


def test_query_hits_include_score_explanations(tmp_path: Path) -> None:
    snapshot = index_path(_mixed_repo(tmp_path), namespace="fixture")

    result = query(snapshot, QueryRequest(query="RuntimeGraph", max_results=3))

    assert result.hits
    assert result.hits[0].explanation.matched_fields
    assert "RuntimeGraph".lower() in result.hits[0].explanation.matched_tokens
    assert result.hits[0].to_dict()["explanation"]["score_parts"]


def test_refresh_snapshot_reports_changed_unchanged_and_removed_paths(
    tmp_path: Path,
) -> None:
    root = _mixed_repo(tmp_path)
    first = refresh_snapshot(root, namespace="fixture")
    (root / "README.md").write_text("# Project\n\n## New\n", encoding="utf-8")
    (root / "package.json").unlink()

    second = refresh_snapshot(
        root, namespace="fixture", previous_manifest=first.manifest
    )

    assert "README.md" in second.changed_paths
    assert "src/app.py" in second.unchanged_paths
    assert "package.json" in second.removed_paths
    assert second.snapshot.stats["parser_count"] >= 1


def test_scope_policy_omits_large_files_without_indexing_content(
    tmp_path: Path,
) -> None:
    root = _mixed_repo(tmp_path)
    (root / "huge.txt").write_text("x" * 32, encoding="utf-8")

    snapshot = index_path(
        root, namespace="fixture", policy=ScopePolicy(max_file_bytes=8)
    )

    assert any(
        item.reason == "max_file_size" and item.item_id == "huge.txt"
        for item in snapshot.omitted
    )
    assert not any(node.source_ref.path == "huge.txt" for node in snapshot.nodes)


def test_cli_refresh_and_explain_commands(tmp_path: Path) -> None:
    root = _mixed_repo(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    manifest_path = tmp_path / "manifest.json"

    refresh = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "refresh",
            str(root),
            "--out",
            str(snapshot_path),
            "--manifest-out",
            str(manifest_path),
            "--namespace",
            "fixture",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    explain = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "explain",
            str(snapshot_path),
            "RuntimeGraph",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "src/app.py" in json.loads(refresh.stdout)["changed_paths"]
    assert json.loads(explain.stdout)["hits"][0]["explanation"]["score_parts"]


def test_expanded_handoff_fixture_contracts_are_stable(tmp_path: Path) -> None:
    fixture = fixture_repo("mixed_repo")
    explain_contract = json.loads(
        contract_path("expected_explain_runtimegraph.json").read_text()
    )
    refresh_contract = json.loads(
        contract_path("expected_refresh_paths.json").read_text()
    )

    snapshot = index_path(fixture, namespace="fixture")
    explained = query(
        snapshot,
        QueryRequest(query=explain_contract["expected"]["query"], max_results=1),
    )
    first_hit = explained.hits[0]
    first = refresh_snapshot(fixture, namespace="fixture")
    copy_root = tmp_path / "fixture_copy"
    shutil.copytree(fixture, copy_root)
    (copy_root / "README.md").write_text("# Changed\n", encoding="utf-8")
    (copy_root / "package.json").unlink()
    second = refresh_snapshot(
        copy_root, namespace="fixture", previous_manifest=first.manifest
    )

    assert first_hit.node.kind == explain_contract["expected"]["first_hit_kind"]
    assert first_hit.node.label == explain_contract["expected"]["first_hit_label"]
    assert first_hit.explanation.score_parts
    assert refresh_contract["expected"]["changed_path"] in second.changed_paths
    assert refresh_contract["expected"]["unchanged_path"] in second.unchanged_paths
    assert refresh_contract["expected"]["removed_path"] in second.removed_paths
