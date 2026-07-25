"""Storage exports for canonical PragmaGraph snapshots and materialized stores."""

from __future__ import annotations

from pragmagraph.storage.backends import (
    GraphStore,
    JsonSnapshotStore,
    SQLiteGraphStore,
    StoreCapabilityReport,
    StoreManifest,
    StoreSearchExplanation,
    StoreUpdateReport,
    explain_store_query,
    open_store,
)
from pragmagraph.storage.roundtrip import (
    StoreRoundTripReport,
    verify_existing_store_round_trip,
    verify_store_round_trip,
)
from pragmagraph.storage.registry import (
    BackendCatalogEntry,
    backend_capabilities_for_path,
    backend_catalog_payload,
    build_backend_catalog,
)
from pragmagraph.storage.snapshots import (
    SnapshotRepository,
    load_snapshot,
    save_snapshot,
    snapshot_from_dict,
    snapshot_to_dict,
    stable_dumps,
)

__all__ = [
    "GraphStore",
    "JsonSnapshotStore",
    "SQLiteGraphStore",
    "SnapshotRepository",
    "BackendCatalogEntry",
    "StoreCapabilityReport",
    "StoreManifest",
    "StoreRoundTripReport",
    "StoreSearchExplanation",
    "StoreUpdateReport",
    "backend_capabilities_for_path",
    "backend_catalog_payload",
    "build_backend_catalog",
    "explain_store_query",
    "load_snapshot",
    "open_store",
    "save_snapshot",
    "snapshot_from_dict",
    "snapshot_to_dict",
    "stable_dumps",
    "verify_existing_store_round_trip",
    "verify_store_round_trip",
]
