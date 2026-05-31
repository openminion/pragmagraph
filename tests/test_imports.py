from __future__ import annotations

from pathlib import Path
import tomllib


def test_pragmagraph_package_imports() -> None:
    import pragmagraph
    import pragmagraph.adapters
    import pragmagraph.contracts
    import pragmagraph.models
    import pragmagraph.portability
    import pragmagraph.query
    import pragmagraph.storage

    assert pragmagraph.__version__ == "0.0.1"
    assert pragmagraph.PACKAGE_STATUS == "semantic-alpha"
    assert "pragmagraph.models" in pragmagraph.STABLE_IMPORT_ROOTS
    assert "GraphNode" in pragmagraph.models.__all__
    assert "query" in pragmagraph.query.__all__
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
        "GraphSnapshot",
        "HealthSummary",
        "INDEXER_VERSION",
        "OmittedDiagnostic",
        "PathResult",
        "PragmaGraphError",
        "QueryHit",
        "QueryRequest",
        "QueryResult",
        "SCHEMA_VERSION",
        "SourceRef",
        "index_path",
        "load_snapshot",
        "save_snapshot",
        "stable_dumps",
    }
    assert all(
        not (name.startswith("_") and not name.endswith("__"))
        for name in pragmagraph.__all__
    )


def test_public_roots_expose_semantic_alpha_contracts() -> None:
    import pragmagraph.adapters as adapters
    import pragmagraph.contracts as contracts
    import pragmagraph.models as models
    import pragmagraph.portability as portability
    import pragmagraph.query as query
    import pragmagraph.storage as storage

    assert "index_path" in adapters.__all__
    assert "SCHEMA_VERSION" in contracts.__all__
    assert "GraphSnapshot" in models.__all__
    assert "pragma_uri" in portability.__all__
    assert "neighborhood" in query.__all__
    assert "save_snapshot" in storage.__all__


def test_pragmagraph_package_does_not_import_openminion_from_source() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "pragmagraph"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text()
        if "import openminion" in text or "from openminion" in text:
            offenders.append(str(path))
    assert offenders == []
