"""Store backends over canonical PragmaGraph snapshots."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Protocol

from pragmagraph._immutables import frozen_mapping, tuple_str
from pragmagraph.contracts import SCHEMA_VERSION
from pragmagraph.models import (
    GraphSnapshot,
    HealthSummary,
    PathResult,
    PragmaGraphError,
    QueryRequest,
    QueryResult,
)
from pragmagraph.query import health, neighborhood, path, query
from pragmagraph.storage import (
    load_snapshot,
    save_snapshot,
    snapshot_from_dict,
    snapshot_to_dict,
    stable_dumps,
)

STORE_MANIFEST_SCHEMA_VERSION = "pragmagraph.store_manifest.v1alpha1"
SQLITE_STORE_SCHEMA_VERSION = "pragmagraph.sqlite_store.v1alpha1"


@dataclass(frozen=True)
class StoreManifest:
    """Deterministic store manifest for rebuildable materialized stores."""

    backend: str
    schema_version: str
    snapshot_schema_version: str = SCHEMA_VERSION
    namespace: str = "default"
    node_count: int = 0
    edge_count: int = 0
    omitted_count: int = 0
    source_ref_count: int = 0
    fts_available: bool = False
    diagnostics: tuple[str, ...] = ()
    manifest_schema_version: str = STORE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "backend", str(self.backend))
        object.__setattr__(self, "schema_version", str(self.schema_version))
        object.__setattr__(
            self, "snapshot_schema_version", str(self.snapshot_schema_version)
        )
        object.__setattr__(self, "namespace", str(self.namespace or "default"))
        object.__setattr__(self, "node_count", max(0, int(self.node_count or 0)))
        object.__setattr__(self, "edge_count", max(0, int(self.edge_count or 0)))
        object.__setattr__(self, "omitted_count", max(0, int(self.omitted_count or 0)))
        object.__setattr__(
            self,
            "source_ref_count",
            max(0, int(self.source_ref_count or 0)),
        )
        object.__setattr__(self, "diagnostics", tuple_str(self.diagnostics))
        object.__setattr__(
            self,
            "manifest_schema_version",
            str(self.manifest_schema_version or STORE_MANIFEST_SCHEMA_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_payload(self)
        payload["diagnostics"] = list(self.diagnostics)
        return payload


@dataclass(frozen=True)
class StoreCapabilityReport:
    """Advertised behavior for one store backend instance."""

    backend: str
    readable: bool
    writable: bool
    query_supported: bool
    lexical_search_supported: bool
    neighborhood_supported: bool
    path_supported: bool
    import_export_supported: bool
    fts_available: bool = False
    unsupported_modes: tuple[str, ...] = ()
    diagnostics: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "backend", str(self.backend))
        object.__setattr__(self, "unsupported_modes", tuple_str(self.unsupported_modes))
        object.__setattr__(
            self,
            "diagnostics",
            frozen_mapping(
                {str(key): str(value) for key, value in self.diagnostics.items()}
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_payload(self)
        payload["unsupported_modes"] = list(self.unsupported_modes)
        payload["diagnostics"] = dict(self.diagnostics)
        return payload


class GraphStore(Protocol):
    """Storage contract for canonical and materialized graph stores."""

    def manifest(self) -> StoreManifest:
        """Return deterministic store metadata."""

    def capabilities(self) -> StoreCapabilityReport:
        """Return supported operations and typed capability diagnostics."""

    def import_snapshot(self, snapshot: GraphSnapshot) -> None:
        """Replace store contents with ``snapshot``."""

    def export_snapshot(self) -> GraphSnapshot:
        """Export canonical snapshot truth from the store."""

    def query(self, request: QueryRequest | str) -> QueryResult:
        """Run query through the store contract."""

    def neighborhood(
        self,
        node_id: str,
        *,
        depth: int = 1,
        max_results: int = 10,
    ) -> QueryResult:
        """Return nodes around ``node_id`` through the store contract."""

    def path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_hops: int = 4,
    ) -> PathResult:
        """Return one bounded path through the store contract."""

    def health(self) -> HealthSummary:
        """Return health over the exported canonical snapshot."""


class JsonSnapshotStore:
    """Canonical JSON snapshot store and oracle backend."""

    backend = "json"

    def __init__(
        self,
        snapshot: GraphSnapshot,
        *,
        path: str | Path | None = None,
    ) -> None:
        self._snapshot = snapshot
        self.path = Path(path) if path is not None else None

    @classmethod
    def from_path(cls, path: str | Path) -> "JsonSnapshotStore":
        return cls(load_snapshot(path), path=path)

    def manifest(self) -> StoreManifest:
        return _manifest_for_snapshot(
            self._snapshot,
            backend=self.backend,
            schema_version=self._snapshot.schema_version,
            fts_available=False,
        )

    def capabilities(self) -> StoreCapabilityReport:
        return StoreCapabilityReport(
            backend=self.backend,
            readable=True,
            writable=True,
            query_supported=True,
            lexical_search_supported=True,
            neighborhood_supported=True,
            path_supported=True,
            import_export_supported=True,
            unsupported_modes=("fts", "materialized_sql"),
            diagnostics={"fts": "json_snapshot_store_scans_canonical_snapshot"},
        )

    def import_snapshot(self, snapshot: GraphSnapshot) -> None:
        self._snapshot = snapshot
        if self.path is not None:
            save_snapshot(snapshot, self.path)

    def export_snapshot(self) -> GraphSnapshot:
        return snapshot_from_dict(snapshot_to_dict(self._snapshot))

    def query(self, request: QueryRequest | str) -> QueryResult:
        return query(self._snapshot, request)

    def neighborhood(
        self,
        node_id: str,
        *,
        depth: int = 1,
        max_results: int = 10,
    ) -> QueryResult:
        return neighborhood(
            self._snapshot, node_id, depth=depth, max_results=max_results
        )

    def path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_hops: int = 4,
    ) -> PathResult:
        return path(self._snapshot, source_id, target_id, max_hops=max_hops)

    def health(self) -> HealthSummary:
        return health(self._snapshot)


class SQLiteGraphStore:
    """SQLite materialized store over canonical snapshot facts."""

    backend = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.store_path = Path(path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_snapshot(
        cls, snapshot: GraphSnapshot, path: str | Path
    ) -> "SQLiteGraphStore":
        store = cls(path)
        store.import_snapshot(snapshot)
        return store

    def import_snapshot(self, snapshot: GraphSnapshot) -> None:
        with self._connect() as connection:
            _initialize_sqlite_schema(connection)
            fts_available, diagnostics = _initialize_fts(connection)
            connection.execute("DELETE FROM store_manifest")
            connection.execute("DELETE FROM snapshots")
            connection.execute("DELETE FROM nodes")
            connection.execute("DELETE FROM edges")
            connection.execute("DELETE FROM omitted")
            connection.execute("DELETE FROM source_refs")
            if fts_available:
                connection.execute("DELETE FROM node_fts")
            connection.execute(
                "INSERT INTO snapshots (id, payload) VALUES (?, ?)",
                ("current", stable_dumps(snapshot)),
            )
            for node in sorted(snapshot.nodes, key=lambda item: item.id):
                connection.execute(
                    """
                    INSERT INTO nodes
                    (id, kind, label, source_path, text, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node.id,
                        node.kind,
                        node.label,
                        node.source_ref.path,
                        node.text,
                        json.dumps(node.to_dict(), sort_keys=True),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO source_refs
                    (owner_type, owner_id, path, line, column, section, uri)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    _source_ref_row("node", node.id, node.source_ref),
                )
                if fts_available:
                    connection.execute(
                        """
                        INSERT INTO node_fts
                        (id, kind, label, source_path, text, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            node.id,
                            node.kind,
                            node.label,
                            node.source_ref.path,
                            node.text,
                            " ".join(str(value) for value in node.metadata.values()),
                        ),
                    )
            for edge in sorted(snapshot.edges, key=lambda item: item.id):
                connection.execute(
                    """
                    INSERT INTO edges
                    (id, kind, source_id, target_id, source_path, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge.id,
                        edge.kind,
                        edge.source_id,
                        edge.target_id,
                        edge.source_ref.path,
                        json.dumps(edge.to_dict(), sort_keys=True),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO source_refs
                    (owner_type, owner_id, path, line, column, section, uri)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    _source_ref_row("edge", edge.id, edge.source_ref),
                )
            for item in sorted(
                snapshot.omitted, key=lambda value: (value.reason, value.item_id)
            ):
                connection.execute(
                    """
                    INSERT INTO omitted (reason, item_id, payload)
                    VALUES (?, ?, ?)
                    """,
                    (
                        item.reason,
                        item.item_id,
                        json.dumps(item.to_dict(), sort_keys=True),
                    ),
                )
            manifest = _manifest_for_snapshot(
                snapshot,
                backend=self.backend,
                schema_version=SQLITE_STORE_SCHEMA_VERSION,
                fts_available=fts_available,
                diagnostics=tuple(diagnostics),
            )
            connection.execute(
                "INSERT INTO store_manifest (id, payload) VALUES (?, ?)",
                ("current", json.dumps(manifest.to_dict(), sort_keys=True)),
            )

    def manifest(self) -> StoreManifest:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM store_manifest WHERE id = ?",
                ("current",),
            ).fetchone()
        if row is None:
            raise _store_error(
                "store manifest not found",
                code="STORE_MANIFEST_NOT_FOUND",
                details={"path": str(self.store_path)},
            )
        return _manifest_from_dict(json.loads(str(row["payload"])))

    def capabilities(self) -> StoreCapabilityReport:
        manifest = self.manifest()
        diagnostics = {}
        if not manifest.fts_available:
            diagnostics["fts"] = (
                "sqlite_fts5_unavailable; lexical search falls back to stable SQL scan"
            )
        return StoreCapabilityReport(
            backend=self.backend,
            readable=True,
            writable=True,
            query_supported=True,
            lexical_search_supported=True,
            neighborhood_supported=True,
            path_supported=True,
            import_export_supported=True,
            fts_available=manifest.fts_available,
            unsupported_modes=("vector", "remote_service"),
            diagnostics=diagnostics,
        )

    def export_snapshot(self) -> GraphSnapshot:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM snapshots WHERE id = ?",
                ("current",),
            ).fetchone()
        if row is None:
            raise _store_error(
                "store snapshot not found",
                code="STORE_SNAPSHOT_NOT_FOUND",
                details={"path": str(self.store_path)},
            )
        payload = json.loads(str(row["payload"]))
        if not isinstance(payload, dict):
            raise _store_error(
                "store snapshot payload must be an object",
                code="INVALID_STORE_SNAPSHOT",
                details={"path": str(self.store_path)},
            )
        return snapshot_from_dict(payload)

    def query(self, request: QueryRequest | str) -> QueryResult:
        req = (
            request
            if isinstance(request, QueryRequest)
            else QueryRequest(query=request)
        )
        snapshot = self.export_snapshot()
        result = query(snapshot, req)
        manifest = self.manifest()
        diagnostics = dict(result.diagnostics)
        diagnostics["store_backend"] = self.backend
        diagnostics["fts_available"] = manifest.fts_available
        diagnostics["candidate_node_ids"] = list(
            _sqlite_candidate_node_ids(
                self.store_path,
                req.query,
                req.max_results * 4,
            )
        )
        return QueryResult(
            query=result.query,
            hits=result.hits,
            omitted=result.omitted,
            diagnostics=diagnostics,
        )

    def neighborhood(
        self,
        node_id: str,
        *,
        depth: int = 1,
        max_results: int = 10,
    ) -> QueryResult:
        return neighborhood(
            self.export_snapshot(),
            node_id,
            depth=depth,
            max_results=max_results,
        )

    def path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_hops: int = 4,
    ) -> PathResult:
        return path(
            self.export_snapshot(),
            source_id,
            target_id,
            max_hops=max_hops,
        )

    def health(self) -> HealthSummary:
        return health(self.export_snapshot())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.store_path)
        connection.row_factory = sqlite3.Row
        return connection


def open_store(path: str | Path, *, backend: str = "sqlite") -> GraphStore:
    """Open a concrete graph store by backend name."""
    if backend == "sqlite":
        return SQLiteGraphStore(path)
    if backend == "json":
        return JsonSnapshotStore.from_path(path)
    raise _store_error(
        "unsupported graph store backend",
        code="STORE_BACKEND_UNSUPPORTED",
        details={"backend": backend, "supported": ["json", "sqlite"]},
    )


def _initialize_sqlite_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS store_manifest (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS snapshots (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            label TEXT NOT NULL,
            source_path TEXT NOT NULL,
            text TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS omitted (
            reason TEXT NOT NULL,
            item_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (reason, item_id)
        );
        CREATE TABLE IF NOT EXISTS source_refs (
            owner_type TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            path TEXT NOT NULL,
            line INTEGER,
            column INTEGER,
            section TEXT NOT NULL,
            uri TEXT NOT NULL,
            PRIMARY KEY (owner_type, owner_id)
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
        CREATE INDEX IF NOT EXISTS idx_nodes_source_path ON nodes(source_path);
        CREATE INDEX IF NOT EXISTS idx_edges_source_id ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target_id ON edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
        CREATE INDEX IF NOT EXISTS idx_omitted_reason ON omitted(reason);
        """
    )


def _initialize_fts(connection: sqlite3.Connection) -> tuple[bool, list[str]]:
    try:
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS node_fts
            USING fts5(id, kind, label, source_path, text, metadata)
            """
        )
    except sqlite3.OperationalError:
        return False, ["sqlite_fts5_unavailable"]
    return True, []


def _sqlite_candidate_node_ids(
    store_path: Path,
    query_text: str,
    limit: int,
) -> tuple[str, ...]:
    query_text = query_text.strip()
    if not query_text:
        return ()
    with sqlite3.connect(store_path) as connection:
        connection.row_factory = sqlite3.Row
        manifest = SQLiteGraphStore(store_path).manifest()
        if manifest.fts_available:
            rows = connection.execute(
                """
                SELECT id FROM node_fts
                WHERE node_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (_escape_fts_query(query_text), max(1, limit)),
            ).fetchall()
        else:
            pattern = f"%{query_text}%"
            rows = connection.execute(
                """
                SELECT id FROM nodes
                WHERE id LIKE ? OR kind LIKE ? OR label LIKE ?
                   OR source_path LIKE ? OR text LIKE ?
                ORDER BY kind, source_path, id
                LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, pattern, max(1, limit)),
            ).fetchall()
    return tuple(str(row["id"]) for row in rows)


def _escape_fts_query(query_text: str) -> str:
    tokens = [token for token in query_text.replace('"', " ").split() if token]
    return " OR ".join(f'"{token}"' for token in tokens) or '""'


def _source_ref_row(owner_type: str, owner_id: str, source_ref: Any) -> tuple[Any, ...]:
    return (
        owner_type,
        owner_id,
        source_ref.path,
        source_ref.line,
        source_ref.column,
        source_ref.section,
        source_ref.uri,
    )


def _manifest_for_snapshot(
    snapshot: GraphSnapshot,
    *,
    backend: str,
    schema_version: str,
    fts_available: bool,
    diagnostics: tuple[str, ...] = (),
) -> StoreManifest:
    return StoreManifest(
        backend=backend,
        schema_version=schema_version,
        snapshot_schema_version=snapshot.schema_version,
        namespace=snapshot.namespace,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        omitted_count=len(snapshot.omitted),
        source_ref_count=len(snapshot.nodes) + len(snapshot.edges),
        fts_available=fts_available,
        diagnostics=diagnostics,
    )


def _manifest_from_dict(payload: dict[str, Any]) -> StoreManifest:
    return StoreManifest(
        manifest_schema_version=str(
            payload.get("manifest_schema_version", STORE_MANIFEST_SCHEMA_VERSION)
        ),
        backend=str(payload.get("backend", "")),
        schema_version=str(payload.get("schema_version", "")),
        snapshot_schema_version=str(payload.get("snapshot_schema_version", "")),
        namespace=str(payload.get("namespace", "") or "default"),
        node_count=int(payload.get("node_count", 0) or 0),
        edge_count=int(payload.get("edge_count", 0) or 0),
        omitted_count=int(payload.get("omitted_count", 0) or 0),
        source_ref_count=int(payload.get("source_ref_count", 0) or 0),
        fts_available=bool(payload.get("fts_available", False)),
        diagnostics=tuple_str(payload.get("diagnostics", ())),
    )


def _store_error(
    message: str,
    *,
    code: str,
    details: dict[str, Any] | None = None,
) -> PragmaGraphError:
    return PragmaGraphError(message, code=code, details=details or {})


def _dataclass_payload(value: Any) -> dict[str, Any]:
    return {item.name: getattr(value, item.name) for item in fields(value)}


__all__ = [
    "GraphStore",
    "JsonSnapshotStore",
    "SQLITE_STORE_SCHEMA_VERSION",
    "STORE_MANIFEST_SCHEMA_VERSION",
    "SQLiteGraphStore",
    "StoreCapabilityReport",
    "StoreManifest",
    "open_store",
]
