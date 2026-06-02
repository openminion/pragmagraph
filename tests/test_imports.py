from __future__ import annotations

from pathlib import Path
import tomllib


def test_pragmagraph_package_imports() -> None:
    import pragmagraph
    import pragmagraph.adapters
    import pragmagraph.contracts
    import pragmagraph.export
    import pragmagraph.graphify
    import pragmagraph.models
    import pragmagraph.parsers
    import pragmagraph.portability
    import pragmagraph.query
    import pragmagraph.report
    import pragmagraph.refresh
    import pragmagraph.security
    import pragmagraph.storage

    assert pragmagraph.__version__ == "0.0.1"
    assert pragmagraph.PACKAGE_STATUS == "semantic-alpha"
    assert "pragmagraph.models" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.export" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.graphify" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.report" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "render_dot" in pragmagraph.export.__all__
    assert "to_graphify_payload" in pragmagraph.graphify.__all__
    assert "GraphNode" in pragmagraph.models.__all__
    assert "query" in pragmagraph.query.__all__
    assert "build_report" in pragmagraph.report.__all__
    assert "load_snapshot" in pragmagraph.storage.__all__


def test_top_level_public_api_and_version_metadata_are_stable() -> None:
    import pragmagraph

    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())

    assert pragmagraph.__version__ == pyproject["project"]["version"]
    assert set(pragmagraph.__all__) == {
        "PACKAGE_STATUS",
        "STABLE_IMPORT_ROOTS",
        "__version__",
        "CAPABILITIES",
        "GraphEdge",
        "GraphNode",
        "GraphReport",
        "GraphReportDependency",
        "GraphReportFinding",
        "GraphReportNode",
        "GraphReportSummary",
        "GraphSnapshot",
        "GRAPHIFY_INTEROP_FORMAT",
        "HealthSummary",
        "INDEXER_VERSION",
        "OmittedDiagnostic",
        "PathResult",
        "ParserDiagnostic",
        "ParserResult",
        "PragmaGraphError",
        "QueryExplanation",
        "QueryHit",
        "QueryRequest",
        "QueryResult",
        "RefreshManifest",
        "RefreshManifestEntry",
        "RefreshResult",
        "SCHEMA_VERSION",
        "SourceRef",
        "build_report",
        "index_path",
        "load_snapshot",
        "render_dot",
        "render_graph_export",
        "render_mermaid",
        "render_markdown_report",
        "refresh_snapshot",
        "save_snapshot",
        "snapshot_from_graphify_payload",
        "stable_dumps",
        "to_graphify_payload",
    }
    assert all(
        not (name.startswith("_") and not name.endswith("__"))
        for name in pragmagraph.__all__
    )


def test_public_roots_expose_semantic_alpha_contracts() -> None:
    import pragmagraph.adapters as adapters
    import pragmagraph.contracts as contracts
    import pragmagraph.export as export
    import pragmagraph.graphify as graphify
    import pragmagraph.models as models
    import pragmagraph.parsers as parsers
    import pragmagraph.portability as portability
    import pragmagraph.query as query
    import pragmagraph.report as report
    import pragmagraph.refresh as refresh
    import pragmagraph.security as security
    import pragmagraph.storage as storage

    assert "index_path" in adapters.__all__
    assert "SCHEMA_VERSION" in contracts.__all__
    assert "render_mermaid" in export.__all__
    assert "snapshot_from_graphify_payload" in graphify.__all__
    assert "GraphSnapshot" in models.__all__
    assert "get_default_registry" in parsers.__all__
    assert "pragma_uri" in portability.__all__
    assert "neighborhood" in query.__all__
    assert "render_markdown_report" in report.__all__
    assert "refresh_snapshot" in refresh.__all__
    assert "ScopePolicy" in security.__all__
    assert "save_snapshot" in storage.__all__


def test_pragmagraph_package_does_not_import_openminion_from_source() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "pragmagraph"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text()
        if "import openminion" in text or "from openminion" in text:
            offenders.append(str(path))
    assert offenders == []
