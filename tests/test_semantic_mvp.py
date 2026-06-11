from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pragmagraph.adapters import index_path
from pragmagraph.contracts import NODE_DOC_SECTION, NODE_FILE, NODE_PYTHON_SYMBOL
from pragmagraph.models import QueryRequest
from pragmagraph.portability import node_id, pragma_uri
from pragmagraph.query import health, neighborhood, path, query
from pragmagraph.storage import load_snapshot, save_snapshot, stable_dumps

from .package_paths import contract_path, fixture_repo


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text(
        "# PragmaGraph Fixture\n\n## Runtime Wiring\n\nStatic graph facts.\n",
        encoding="utf-8",
    )
    (root / "src" / "app.py").write_text(
        "import json\n\nclass RuntimeGraph:\n    pass\n\n"
        "def build_runtime_graph():\n    return RuntimeGraph()\n",
        encoding="utf-8",
    )
    return root


def test_models_storage_and_uri_helpers_round_trip(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    snapshot = index_path(root, namespace="fixture")
    target = tmp_path / "snapshot.json"

    save_snapshot(snapshot, target)
    loaded = load_snapshot(target)

    assert loaded.schema_version == snapshot.schema_version
    assert stable_dumps(loaded) == target.read_text(encoding="utf-8")
    assert pragma_uri("fixture", "file", "src/app.py").startswith("pragma://fixture")
    assert node_id("fixture", NODE_FILE, "src/app.py") in {
        node.id for node in loaded.nodes
    }


def test_indexer_extracts_files_markdown_sections_symbols_and_imports(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    snapshot = index_path(root, namespace="fixture")

    by_kind = {}
    for node in snapshot.nodes:
        by_kind.setdefault(node.kind, []).append(node)

    assert any(node.source_ref.path == "README.md" for node in by_kind[NODE_FILE])
    assert any(
        node.kind == NODE_DOC_SECTION and node.label == "Runtime Wiring"
        for node in snapshot.nodes
    )
    assert any(
        node.kind == NODE_PYTHON_SYMBOL and node.label == "RuntimeGraph"
        for node in snapshot.nodes
    )
    assert any(edge.kind == "imports" for edge in snapshot.edges)
    assert health(snapshot).to_dict()["node_count"] == len(snapshot.nodes)


def test_query_neighborhood_and_path_are_cited_and_deterministic(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    snapshot = index_path(root, namespace="fixture")

    result = query(snapshot, QueryRequest(query="RuntimeGraph", max_results=2))

    assert result.hits
    assert result.hits[0].node.source_ref.path == "src/app.py"
    assert result.hits[0].snippet
    assert (
        result.to_dict()
        == query(
            snapshot,
            QueryRequest(query="RuntimeGraph", max_results=2),
        ).to_dict()
    )

    file_id = node_id("fixture", NODE_FILE, "src/app.py")
    symbol_id = node_id("fixture", NODE_PYTHON_SYMBOL, "src/app.py:RuntimeGraph")
    neighbors = neighborhood(snapshot, file_id)
    assert any(hit.node.id == symbol_id for hit in neighbors.hits)

    path_result = path(snapshot, file_id, symbol_id, max_hops=2)
    assert [node.id for node in path_result.nodes] == [file_id, symbol_id]
    assert path_result.edges[0].kind == "defines"


def test_query_records_omitted_diagnostics_when_budget_truncates(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    snapshot = index_path(root, namespace="fixture")

    result = query(snapshot, QueryRequest(query="graph", max_results=1))

    assert len(result.hits) == 1
    assert result.omitted
    assert result.omitted[0].reason == "max_results"


def test_cli_index_query_health(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "index",
            str(root),
            "--out",
            str(snapshot_path),
            "--namespace",
            "fixture",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    query_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "query",
            str(snapshot_path),
            "RuntimeGraph",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(query_result.stdout)

    assert payload["hits"][0]["node"]["source_ref"]["path"] == "src/app.py"
    assert (
        json.loads(
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pragmagraph",
                    "health",
                    str(snapshot_path),
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )["ok"]
        is True
    )


def test_invalid_snapshot_schema_is_typed_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version": "nope"}', encoding="utf-8")

    with pytest.raises(Exception) as exc_info:
        load_snapshot(path)

    assert getattr(exc_info.value, "code") == "UNSUPPORTED_SCHEMA_VERSION"


def test_openminion_handoff_artifacts_match_fixture_contract() -> None:
    fixture = fixture_repo("tiny_repo")
    capabilities = json.loads(contract_path("capabilities.json").read_text())
    expected = json.loads(contract_path("expected_query_runtimegraph.json").read_text())
    errors = json.loads(contract_path("typed_errors.json").read_text())

    snapshot = index_path(fixture, namespace="fixture")
    result = query(snapshot, QueryRequest(query=expected["expected"]["query"]))

    assert capabilities["provider"] == "pragmagraph"
    assert capabilities["semantic_contract"] is True
    assert "query" in capabilities["capabilities"]
    assert result.hits[0].node.kind == expected["expected"]["first_hit_kind"]
    assert result.hits[0].node.label == expected["expected"]["first_hit_label"]
    assert result.hits[0].node.source_ref.path == expected["expected"]["first_hit_path"]
    assert {item["code"] for item in errors["errors"]} >= {
        "SNAPSHOT_NOT_FOUND",
        "UNSUPPORTED_SCHEMA_VERSION",
    }
