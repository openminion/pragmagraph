"""Backend capability registry for PragmaGraph storage surfaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from pragmagraph.models import PragmaGraphError
from pragmagraph.storage.backends import JsonSnapshotStore, SQLiteGraphStore


@dataclass(frozen=True, slots=True)
class BackendCatalogEntry:
    """One advertised storage/search backend posture."""

    backend: str
    status: str
    canonical: bool
    materialized: bool
    query_supported: bool
    lexical_search_supported: bool
    import_export_supported: bool
    optional_dependency: str = ""
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["diagnostics"] = list(self.diagnostics)
        return payload


def build_backend_catalog() -> tuple[BackendCatalogEntry, ...]:
    """Return the package-level backend catalog without importing optional stores."""
    return (
        BackendCatalogEntry(
            backend="json",
            status="available",
            canonical=True,
            materialized=False,
            query_supported=True,
            lexical_search_supported=True,
            import_export_supported=True,
            diagnostics=("canonical_snapshot_oracle",),
        ),
        BackendCatalogEntry(
            backend="sqlite",
            status="available",
            canonical=False,
            materialized=True,
            query_supported=True,
            lexical_search_supported=True,
            import_export_supported=True,
            diagnostics=("materialized_rebuildable_index",),
        ),
        BackendCatalogEntry(
            backend="kuzu",
            status="reserved",
            canonical=False,
            materialized=True,
            query_supported=False,
            lexical_search_supported=False,
            import_export_supported=False,
            optional_dependency="kuzu",
            diagnostics=("deferred_backend_requires_separate_scope_acceptance",),
        ),
        BackendCatalogEntry(
            backend="duckdb",
            status="reserved",
            canonical=False,
            materialized=True,
            query_supported=False,
            lexical_search_supported=False,
            import_export_supported=False,
            optional_dependency="duckdb",
            diagnostics=("deferred_backend_requires_separate_scope_acceptance",),
        ),
        BackendCatalogEntry(
            backend="vector_sidecar",
            status="boundary_reserve",
            canonical=False,
            materialized=True,
            query_supported=False,
            lexical_search_supported=False,
            import_export_supported=False,
            diagnostics=("requires_boundary_acceptance_before_vector_retrieval",),
        ),
    )


def backend_catalog_payload() -> dict[str, object]:
    """Return a stable JSON payload for CLI and doctor surfaces."""
    entries = build_backend_catalog()
    return {
        "schema_version": "pragmagraph.storage_backend_catalog.v1alpha1",
        "canonical_backend": "json",
        "default_materialized_backend": "sqlite",
        "entries": [entry.to_dict() for entry in entries],
    }


def backend_capabilities_for_path(
    backend: str,
    path: str | Path,
) -> dict[str, object]:
    """Inspect one concrete backend path and return typed capabilities."""
    if backend == "json":
        return JsonSnapshotStore.from_path(path).capabilities().to_dict()
    if backend == "sqlite":
        return SQLiteGraphStore(path).capabilities().to_dict()
    raise PragmaGraphError(
        "unsupported storage backend",
        code="STORE_BACKEND_UNSUPPORTED",
        details={
            "backend": backend,
            "supported": [entry.backend for entry in build_backend_catalog()],
        },
    )


__all__ = [
    "BackendCatalogEntry",
    "backend_capabilities_for_path",
    "backend_catalog_payload",
    "build_backend_catalog",
]
