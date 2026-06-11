from __future__ import annotations

from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.query import neighborhood
from pragmagraph.parsers import OptionalParserFamily, ParserRegistry, PythonAstParser
from pragmagraph.query import backlinks, impact, reverse_dependencies, reverse_imports
from pragmagraph.refresh import refresh_snapshot


def _script_repo(tmp_path: Path) -> Path:
    root = tmp_path / "script-repo"
    (root / "src").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "README.md").write_text(
        "# Runtime Graph\n\nSee [Guide](docs/guide.md#Install).\n",
        encoding="utf-8",
    )
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\n## Install\n\nSee [Runtime](../README.md#Runtime-Graph).\n",
        encoding="utf-8",
    )
    (root / "src" / "index.ts").write_text(
        "import { makeValue } from './util';\n"
        "export function buildRuntimeGraph() {\n"
        "  return makeValue();\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "src" / "util.ts").write_text(
        "export function makeValue() {\n  return true;\n}\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        '{"dependencies":{"left-pad":"1.0.0"}}\n',
        encoding="utf-8",
    )
    return root


def test_script_parser_extracts_modules_imports_and_exports(tmp_path: Path) -> None:
    snapshot = index_path(_script_repo(tmp_path), namespace="fixture")

    assert any(node.kind == "script_module" for node in snapshot.nodes)
    assert any(
        node.kind == "script_function" and node.label == "buildRuntimeGraph"
        for node in snapshot.nodes
    )
    assert any(
        node.kind == "script_export" and node.label == "makeValue"
        for node in snapshot.nodes
    )
    assert any(
        edge.kind == "imports" and edge.metadata.get("resolved") is True
        for edge in snapshot.edges
    )


def test_optional_parser_unavailable_surfaces_typed_diagnostic(
    tmp_path: Path,
) -> None:
    registry = ParserRegistry(
        parsers=(PythonAstParser(),),
        optional_families=(
            OptionalParserFamily(
                name="tree_sitter_typescript",
                suffixes=frozenset({".ts"}),
                dependency="tree_sitter",
            ),
        ),
    )

    snapshot = index_path(
        _script_repo(tmp_path),
        namespace="fixture",
        parser_registry=registry,
    )

    assert any(
        item.reason == "optional_parser_unavailable" for item in snapshot.omitted
    )


def test_refresh_result_exposes_path_change_reasons_and_snapshot_delta(
    tmp_path: Path,
) -> None:
    root = _script_repo(tmp_path)
    first = refresh_snapshot(root, namespace="fixture")
    (root / "src" / "util.ts").write_text(
        "export function makeValue() {\n  return false;\n}\n",
        encoding="utf-8",
    )
    (root / "package.json").unlink()

    second = refresh_snapshot(
        root,
        namespace="fixture",
        previous_manifest=first.manifest,
        previous_snapshot=first.snapshot,
    )

    changes = {item.path: item for item in second.path_changes}
    assert changes["src/util.ts"].status == "changed"
    assert "content_hash_changed" in changes["src/util.ts"].reasons
    assert changes["package.json"].status == "removed"
    assert second.snapshot_delta.removed_node_ids


def test_structural_navigation_helpers_return_high_confidence_results(
    tmp_path: Path,
) -> None:
    snapshot = index_path(_script_repo(tmp_path), namespace="fixture")

    util_module = next(
        node.id
        for node in snapshot.nodes
        if node.kind == "script_module" and node.label == "util"
    )
    dependency_node = next(
        node.id for node in snapshot.nodes if node.label == "left-pad"
    )
    install_section = next(
        node.id
        for node in snapshot.nodes
        if node.kind == "doc_section"
        and node.source_ref.path == "docs/guide.md"
        and node.id.endswith("docs/guide.md#install")
    )

    import_hits = reverse_imports(snapshot, util_module)
    dependency_hits = reverse_dependencies(snapshot, dependency_node)
    backlink_hits = backlinks(snapshot, install_section)
    impact_hits = impact(snapshot, install_section)

    assert any(
        hit.node.kind == "file" and hit.node.source_ref.path == "src/index.ts"
        for hit in import_hits.hits
    )
    assert any(hit.node.kind == "config" for hit in dependency_hits.hits)
    assert any(hit.node.source_ref.path == "README.md" for hit in backlink_hits.hits)
    assert any(hit.node.source_ref.path == "README.md" for hit in impact_hits.hits)


def test_impact_surfaces_heuristic_edges_as_diagnostics() -> None:
    caller_ref = SourceRef(path="src/caller.py")
    callee_ref = SourceRef(path="src/callee.py")
    snapshot = GraphSnapshot(
        namespace="fixture",
        root_path=".",
        nodes=(
            GraphNode(
                id="pragma://fixture/symbol/src/caller.py#call_site",
                kind="symbol",
                label="call_site",
                source_ref=caller_ref,
            ),
            GraphNode(
                id="pragma://fixture/symbol/src/callee.py#dynamic_call",
                kind="symbol",
                label="dynamic_call",
                source_ref=callee_ref,
            ),
        ),
        edges=(
            GraphEdge(
                id="pragma://fixture/edge/calls/app",
                kind="calls",
                source_id="pragma://fixture/symbol/src/caller.py#call_site",
                target_id="pragma://fixture/symbol/src/callee.py#dynamic_call",
                metadata={"resolved": False},
            ),
        ),
    )

    result = impact(snapshot, "pragma://fixture/symbol/src/callee.py#dynamic_call")

    assert result.hits == ()
    assert any(item.reason == "impact_edge_unresolved" for item in result.omitted)
    assert result.diagnostics["resolution_kind"] == "high_confidence_static_only"


def test_neighborhood_filters_stay_deterministic(tmp_path: Path) -> None:
    snapshot = index_path(_script_repo(tmp_path), namespace="fixture")
    target = next(
        node.id
        for node in snapshot.nodes
        if node.kind == "script_module" and node.label == "index"
    )

    result = neighborhood(
        snapshot,
        target,
        depth=2,
        edge_kinds=("parent_symbol", "defines"),
        node_kinds=("script_function", "script_export"),
    )

    assert result.hits
    assert all(
        hit.node.kind in {"script_function", "script_export"} for hit in result.hits
    )
