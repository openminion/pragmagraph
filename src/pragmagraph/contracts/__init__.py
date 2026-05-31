"""Public constants for the PragmaGraph semantic alpha contract."""

from __future__ import annotations

SCHEMA_VERSION = "pragmagraph.snapshot.v1alpha1"
INDEXER_VERSION = "pragmagraph.indexer.v1alpha1"

CAPABILITY_QUERY = "query"
CAPABILITY_NEIGHBORHOOD = "neighborhood"
CAPABILITY_PATH = "path"
CAPABILITY_HEALTH = "health"
CAPABILITY_REFRESH = "refresh"
CAPABILITY_CITATIONS = "citations"
CAPABILITY_PROVENANCE = "provenance"

CAPABILITIES = frozenset(
    {
        CAPABILITY_QUERY,
        CAPABILITY_NEIGHBORHOOD,
        CAPABILITY_PATH,
        CAPABILITY_HEALTH,
        CAPABILITY_REFRESH,
        CAPABILITY_CITATIONS,
        CAPABILITY_PROVENANCE,
    }
)

NODE_PROJECT = "project"
NODE_DIRECTORY = "directory"
NODE_FILE = "file"
NODE_DOC_SECTION = "doc_section"
NODE_PYTHON_SYMBOL = "python_symbol"

NODE_KINDS = frozenset(
    {
        NODE_PROJECT,
        NODE_DIRECTORY,
        NODE_FILE,
        NODE_DOC_SECTION,
        NODE_PYTHON_SYMBOL,
    }
)

EDGE_CONTAINS = "contains"
EDGE_DEFINES = "defines"
EDGE_IMPORTS = "imports"
EDGE_MENTIONS = "mentions"
EDGE_REFERENCES_SECTION = "references_section"

EDGE_KINDS = frozenset(
    {
        EDGE_CONTAINS,
        EDGE_DEFINES,
        EDGE_IMPORTS,
        EDGE_MENTIONS,
        EDGE_REFERENCES_SECTION,
    }
)

__all__ = [
    "CAPABILITIES",
    "CAPABILITY_CITATIONS",
    "CAPABILITY_HEALTH",
    "CAPABILITY_NEIGHBORHOOD",
    "CAPABILITY_PATH",
    "CAPABILITY_PROVENANCE",
    "CAPABILITY_QUERY",
    "CAPABILITY_REFRESH",
    "EDGE_CONTAINS",
    "EDGE_DEFINES",
    "EDGE_IMPORTS",
    "EDGE_KINDS",
    "EDGE_MENTIONS",
    "EDGE_REFERENCES_SECTION",
    "INDEXER_VERSION",
    "NODE_DIRECTORY",
    "NODE_DOC_SECTION",
    "NODE_FILE",
    "NODE_KINDS",
    "NODE_PROJECT",
    "NODE_PYTHON_SYMBOL",
    "SCHEMA_VERSION",
]
