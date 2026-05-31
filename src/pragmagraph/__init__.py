"""Standalone observed-fact graph substrate for code and document structure."""

from __future__ import annotations

from pragmagraph.adapters import index_path
from pragmagraph.contracts import CAPABILITIES, INDEXER_VERSION, SCHEMA_VERSION
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    HealthSummary,
    OmittedDiagnostic,
    PathResult,
    PragmaGraphError,
    QueryHit,
    QueryRequest,
    QueryResult,
    SourceRef,
)
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
    "pragmagraph.portability",
)

__all__ = [
    "CAPABILITIES",
    "GraphEdge",
    "GraphNode",
    "GraphSnapshot",
    "HealthSummary",
    "INDEXER_VERSION",
    "OmittedDiagnostic",
    "PACKAGE_STATUS",
    "PathResult",
    "PragmaGraphError",
    "QueryHit",
    "QueryRequest",
    "QueryResult",
    "SCHEMA_VERSION",
    "STABLE_IMPORT_ROOTS",
    "SourceRef",
    "__version__",
    "index_path",
    "load_snapshot",
    "save_snapshot",
    "stable_dumps",
]
