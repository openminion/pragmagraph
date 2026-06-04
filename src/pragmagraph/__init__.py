"""Standalone observed-fact graph substrate for code and document structure."""

from __future__ import annotations

from pragmagraph.adapters import index_path
from pragmagraph.contracts import CAPABILITIES, INDEXER_VERSION, SCHEMA_VERSION
from pragmagraph.bench import (
    BenchmarkMeasurement,
    BenchmarkReport,
    benchmark_root,
    render_markdown_benchmark,
)
from pragmagraph.export import render_dot, render_graph_export, render_mermaid
from pragmagraph.graphify import (
    GRAPHIFY_INTEROP_FORMAT,
    snapshot_from_graphify_payload,
    to_graphify_payload,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    HealthSummary,
    OmittedDiagnostic,
    PathResult,
    ParserDiagnostic,
    ParserResult,
    PragmaGraphError,
    QueryExplanation,
    QueryHit,
    QueryRequest,
    QueryResult,
    RefreshManifest,
    RefreshManifestEntry,
    RefreshResult,
    SourceRef,
)
from pragmagraph.report import (
    GraphReport,
    GraphReportDependency,
    GraphReportFinding,
    GraphReportNode,
    GraphReportSummary,
    build_report,
    render_markdown_report,
)
from pragmagraph.refresh import refresh_snapshot
from pragmagraph.storage import load_snapshot, save_snapshot, stable_dumps

__version__ = "0.0.1"

PACKAGE_STATUS = "semantic-alpha"
STABLE_IMPORT_ROOTS = (
    "pragmagraph",
    "pragmagraph.contracts",
    "pragmagraph.models",
    "pragmagraph.query",
    "pragmagraph.storage",
    "pragmagraph.adapters",
    "pragmagraph.bench",
    "pragmagraph.portability",
    "pragmagraph.parsers",
    "pragmagraph.export",
    "pragmagraph.graphify",
    "pragmagraph.report",
    "pragmagraph.refresh",
    "pragmagraph.security",
    "pragmagraph.service",
)

__all__ = [
    "CAPABILITIES",
    "BenchmarkMeasurement",
    "BenchmarkReport",
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
    "PACKAGE_STATUS",
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
    "STABLE_IMPORT_ROOTS",
    "SourceRef",
    "__version__",
    "benchmark_root",
    "build_report",
    "index_path",
    "load_snapshot",
    "render_dot",
    "render_graph_export",
    "render_markdown_benchmark",
    "render_mermaid",
    "render_markdown_report",
    "refresh_snapshot",
    "save_snapshot",
    "snapshot_from_graphify_payload",
    "stable_dumps",
    "to_graphify_payload",
]
