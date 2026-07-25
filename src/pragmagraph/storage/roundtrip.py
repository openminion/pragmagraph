"""Store round-trip proof helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pragmagraph.models import GraphSnapshot, QueryRequest
from pragmagraph.storage.backends import (
    SQLiteGraphStore,
    StoreCapabilityReport,
    StoreManifest,
    StoreSearchExplanation,
    explain_store_query,
)
from pragmagraph.storage.snapshots import stable_dumps


@dataclass(frozen=True)
class StoreRoundTripReport:
    """Deterministic proof that a store exports the same canonical snapshot."""

    backend: str
    store_path: str
    namespace: str
    ok: bool
    snapshot_bytes: int
    exported_snapshot_bytes: int
    manifest: StoreManifest
    capabilities: StoreCapabilityReport
    search_explanation: StoreSearchExplanation | None = None
    mode: str = "import_export"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "backend": self.backend,
            "store_path": self.store_path,
            "namespace": self.namespace,
            "ok": self.ok,
            "snapshot_bytes": self.snapshot_bytes,
            "exported_snapshot_bytes": self.exported_snapshot_bytes,
            "manifest": self.manifest.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "search_explanation": (
                self.search_explanation.to_dict()
                if self.search_explanation is not None
                else {}
            ),
        }


def verify_store_round_trip(
    snapshot: GraphSnapshot,
    store_path: str | Path,
    *,
    query_text: str = "",
) -> StoreRoundTripReport:
    """Import, export, and compare canonical snapshot bytes through SQLite."""
    store = SQLiteGraphStore.from_snapshot(snapshot, store_path)
    exported = store.export_snapshot()
    snapshot_payload = stable_dumps(snapshot)
    exported_payload = stable_dumps(exported)
    explanation = None
    if query_text.strip():
        explanation = explain_store_query(
            store,
            QueryRequest(query=query_text.strip()),
        )
    return StoreRoundTripReport(
        backend=store.backend,
        store_path=str(store.store_path),
        namespace=snapshot.namespace,
        ok=snapshot_payload == exported_payload,
        snapshot_bytes=len(snapshot_payload.encode("utf-8")),
        exported_snapshot_bytes=len(exported_payload.encode("utf-8")),
        manifest=store.manifest(),
        capabilities=store.capabilities(),
        search_explanation=explanation,
    )


def verify_existing_store_round_trip(
    snapshot: GraphSnapshot,
    store_path: str | Path,
    *,
    query_text: str = "",
) -> StoreRoundTripReport:
    """Compare an existing materialized store export with a canonical snapshot."""
    store = SQLiteGraphStore(store_path)
    exported = store.export_snapshot()
    snapshot_payload = stable_dumps(snapshot)
    exported_payload = stable_dumps(exported)
    explanation = None
    if query_text.strip():
        explanation = explain_store_query(
            store,
            QueryRequest(query=query_text.strip()),
        )
    return StoreRoundTripReport(
        backend=store.backend,
        store_path=str(store.store_path),
        namespace=snapshot.namespace,
        ok=snapshot_payload == exported_payload,
        snapshot_bytes=len(snapshot_payload.encode("utf-8")),
        exported_snapshot_bytes=len(exported_payload.encode("utf-8")),
        manifest=store.manifest(),
        capabilities=store.capabilities(),
        search_explanation=explanation,
        mode="existing_store_export_compare",
    )


__all__ = [
    "StoreRoundTripReport",
    "verify_existing_store_round_trip",
    "verify_store_round_trip",
]
