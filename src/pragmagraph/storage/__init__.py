"""Deterministic JSON snapshot storage for PragmaGraph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.contracts import SCHEMA_VERSION
from pragmagraph.models import GraphSnapshot, PragmaGraphError


def snapshot_to_dict(snapshot: GraphSnapshot) -> dict[str, Any]:
    """Return a stable JSON-ready mapping for ``snapshot``."""
    nodes = sorted(snapshot.nodes, key=lambda node: node.id)
    edges = sorted(snapshot.edges, key=lambda edge: edge.id)
    omitted = sorted(snapshot.omitted, key=lambda item: (item.reason, item.item_id))
    return GraphSnapshot(
        namespace=snapshot.namespace,
        root_path=snapshot.root_path,
        nodes=tuple(nodes),
        edges=tuple(edges),
        omitted=tuple(omitted),
        stats=dict(snapshot.stats),
        schema_version=snapshot.schema_version,
        indexer_version=snapshot.indexer_version,
        created_at=snapshot.created_at,
    ).to_dict()


def stable_dumps(snapshot: GraphSnapshot) -> str:
    """Serialize a snapshot with stable ordering."""
    return json.dumps(snapshot_to_dict(snapshot), indent=2, sort_keys=True) + "\n"


def snapshot_from_dict(payload: Mapping[str, Any]) -> GraphSnapshot:
    """Build a snapshot from JSON data and validate the schema version."""
    version = str(payload.get("schema_version", "") or "")
    if version != SCHEMA_VERSION:
        raise PragmaGraphError(
            "unsupported PragmaGraph snapshot schema",
            code="UNSUPPORTED_SCHEMA_VERSION",
            details={"expected": SCHEMA_VERSION, "actual": version},
        )
    return GraphSnapshot.from_dict(payload)


def save_snapshot(snapshot: GraphSnapshot, path: str | Path) -> Path:
    """Write ``snapshot`` as deterministic JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(stable_dumps(snapshot), encoding="utf-8")
    return target


def load_snapshot(path: str | Path) -> GraphSnapshot:
    """Load a deterministic JSON snapshot."""
    target = Path(path)
    if not target.exists():
        raise PragmaGraphError(
            "snapshot file not found",
            code="SNAPSHOT_NOT_FOUND",
            details={"path": str(target)},
        )
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "snapshot JSON root must be an object",
            code="INVALID_SNAPSHOT",
            details={"path": str(target)},
        )
    return snapshot_from_dict(payload)


class SnapshotRepository:
    """Tiny read-only repository wrapper for a snapshot path."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> GraphSnapshot:
        return load_snapshot(self.path)


from pragmagraph.storage.backends import (  # noqa: E402
    GraphStore,
    JsonSnapshotStore,
    SQLiteGraphStore,
    StoreCapabilityReport,
    StoreManifest,
    StoreUpdateReport,
    open_store,
)


__all__ = [
    "GraphStore",
    "JsonSnapshotStore",
    "SQLiteGraphStore",
    "SnapshotRepository",
    "StoreCapabilityReport",
    "StoreManifest",
    "StoreUpdateReport",
    "load_snapshot",
    "open_store",
    "save_snapshot",
    "snapshot_from_dict",
    "snapshot_to_dict",
    "stable_dumps",
]
