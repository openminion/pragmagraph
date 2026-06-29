from __future__ import annotations

from pathlib import Path
import tomllib


def test_pragmagraph_package_imports() -> None:
    import pragmagraph
    import pragmagraph.adapters
    import pragmagraph.bench
    import pragmagraph.contracts
    import pragmagraph.evidence
    import pragmagraph.export
    import pragmagraph.graphify
    import pragmagraph.models
    import pragmagraph.navigation
    import pragmagraph.operations
    import pragmagraph.parsers
    import pragmagraph.portability
    import pragmagraph.query
    import pragmagraph.report
    import pragmagraph.refresh
    import pragmagraph.security
    import pragmagraph.service
    import pragmagraph.storage
    import pragmagraph.ui
    import pragmagraph.workspace

    assert pragmagraph.__version__ == "0.0.3"
    assert pragmagraph.PACKAGE_STATUS == "semantic-alpha"
    assert "pragmagraph.bench" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.models" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.navigation" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.evidence" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.export" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.graphify" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.report" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.service" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.ui" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.workspace" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "pragmagraph.operations" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "render_dot" in pragmagraph.export.__all__
    assert "to_graphify_payload" in pragmagraph.graphify.__all__
    assert "benchmark_root" in pragmagraph.bench.__all__
    assert "GraphNode" in pragmagraph.models.__all__
    assert "reverse_imports" in pragmagraph.query.__all__
    assert "query" in pragmagraph.query.__all__
    assert "build_report" in pragmagraph.report.__all__
    assert "load_snapshot" in pragmagraph.storage.__all__
    assert "build_repo_map" in pragmagraph.navigation.__all__


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
        "BenchmarkMeasurement",
        "BenchmarkReport",
        "MemoryEvidenceBundle",
        "MemoryEvidenceRef",
        "GraphEdge",
        "GraphNode",
        "GraphReport",
        "GraphReportDependency",
        "GraphReportFinding",
        "GraphReportGitCommit",
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
        "RefreshOperationResult",
        "RefreshPathChange",
        "RefreshPlan",
        "RefreshProfile",
        "RefreshResult",
        "RefreshStatus",
        "SCHEMA_VERSION",
        "SnapshotStructuralDelta",
        "SourceRef",
        "RepoMap",
        "RepoMapSection",
        "backlinks",
        "benchmark_root",
        "build_repo_map",
        "build_report",
        "build_refresh_plan",
        "build_refresh_profile",
        "collect_memory_evidence",
        "collect_related_memory_evidence",
        "commits_touching_symbol_file",
        "diff_snapshots",
        "evidence_ref_for_node",
        "files_touched_by_commit",
        "impact",
        "index_path",
        "load_refresh_profile",
        "load_refresh_status",
        "load_snapshot",
        "recent_commits_for_path",
        "render_dot",
        "render_graph_export",
        "render_compact_handoff",
        "render_markdown_benchmark",
        "render_markdown_repo_map",
        "render_mermaid",
        "render_markdown_report",
        "refresh_snapshot",
        "refresh_status_from_result",
        "refresh_workspace",
        "reverse_dependencies",
        "reverse_imports",
        "run_refresh_profile",
        "save_refresh_profile",
        "save_refresh_status",
        "save_snapshot",
        "snapshot_evidence_id",
        "snapshot_from_graphify_payload",
        "stable_dumps",
        "to_graphify_payload",
        "verify_memory_evidence_ref",
        "verify_memory_evidence_refs",
        "WorkspaceMetadata",
        "WorkspacePaths",
        "WorkspaceRefreshResult",
        "WorkspaceStatusView",
        "build_workspace_metadata",
        "initialize_workspace",
        "load_workspace_metadata",
        "load_workspace_status",
    }
    assert all(
        not (name.startswith("_") and not name.endswith("__"))
        for name in pragmagraph.__all__
    )


def test_public_roots_expose_semantic_alpha_contracts() -> None:
    import pragmagraph.adapters as adapters
    import pragmagraph.bench as bench
    import pragmagraph.contracts as contracts
    import pragmagraph.evidence as evidence
    import pragmagraph.export as export
    import pragmagraph.graphify as graphify
    import pragmagraph.models as models
    import pragmagraph.navigation as navigation
    import pragmagraph.parsers as parsers
    import pragmagraph.portability as portability
    import pragmagraph.query as query
    import pragmagraph.report as report
    import pragmagraph.refresh as refresh
    import pragmagraph.security as security
    import pragmagraph.service as service
    import pragmagraph.storage as storage
    import pragmagraph.ui as ui
    import pragmagraph.workspace as workspace

    assert "index_path" in adapters.__all__
    assert "render_markdown_benchmark" in bench.__all__
    assert "SCHEMA_VERSION" in contracts.__all__
    assert "collect_memory_evidence" in evidence.__all__
    assert "render_mermaid" in export.__all__
    assert "snapshot_from_graphify_payload" in graphify.__all__
    assert "GraphSnapshot" in models.__all__
    assert "render_compact_handoff" in navigation.__all__
    assert "OptionalParserFamily" in parsers.__all__
    assert "get_default_registry" in parsers.__all__
    assert "pragma_uri" in portability.__all__
    assert "reverse_imports" in query.__all__
    assert "neighborhood" in query.__all__
    assert "render_markdown_report" in report.__all__
    assert "diff_snapshots" in refresh.__all__
    assert "refresh_snapshot" in refresh.__all__
    assert "ScopePolicy" in security.__all__
    assert "LocalQueryService" in service.__all__
    assert "save_snapshot" in storage.__all__
    assert "build_ui_screen_manifest" in ui.__all__
    assert "initialize_workspace" in workspace.__all__


def test_pragmagraph_package_does_not_import_openminion_from_source() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "pragmagraph"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text()
        if "import openminion" in text or "from openminion" in text:
            offenders.append(str(path))
    assert offenders == []
