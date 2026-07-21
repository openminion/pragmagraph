# Storage Interchange

Status: semantic alpha

PragmaGraph keeps deterministic JSON snapshots as the canonical portable
artifact. Materialized stores are rebuildable indexes over that snapshot truth;
they make search and traversal easier to serve, but they do not create new
graph facts.

## Storage Layers

| Layer | Role | Canonical? |
| --- | --- | --- |
| JSON snapshot | Portable graph truth for files, symbols, docs, artifacts, commits, omitted facts, and source refs. | yes |
| `JsonSnapshotStore` | Typed store wrapper over the canonical snapshot; used as the parity oracle for conformance tests. | yes |
| `SQLiteGraphStore` | Local materialized store with node, edge, omitted, source-ref, manifest, snapshot, and optional FTS tables. | no, rebuildable |
| Vector sidecars | Future opt-in retrieval sidecars over snapshot facts. | no, deferred |

## Python API

```python
from pragmagraph.adapters import index_path
from pragmagraph.storage import JsonSnapshotStore, SQLiteGraphStore

snapshot = index_path(".", namespace="demo")

json_store = JsonSnapshotStore(snapshot)
sqlite_store = SQLiteGraphStore.from_snapshot(snapshot, ".pragmagraph/graph.sqlite")

assert json_store.export_snapshot().schema_version == snapshot.schema_version
assert sqlite_store.export_snapshot().schema_version == snapshot.schema_version

print(sqlite_store.query("RuntimeGraph").to_dict())
print(sqlite_store.capabilities().to_dict())
```

SQLite v2 supports an atomic normalized-row delta while deliberately rewriting
the complete canonical snapshot payload. The update report separates bounded
`normalized_rows_written` from whole-snapshot
`snapshot_payload_bytes_written` so callers do not mistake partial row work for
a fully incremental store write.

## CLI

Build a canonical snapshot first:

```bash
pragmagraph index . \
  --out .pragmagraph/snapshot.json \
  --namespace demo \
  --json
```

Import it into SQLite:

```bash
pragmagraph store-import --config .pragmagraph/workspace.toml --json

pragmagraph store-import .pragmagraph/snapshot.json \
  --out .pragmagraph/graph.sqlite
```

Query, inspect, and export the store:

```bash
pragmagraph store-query --config .pragmagraph/workspace.toml RuntimeGraph --json
pragmagraph store-search-explain --config .pragmagraph/workspace.toml RuntimeGraph --json
pragmagraph store-health --config .pragmagraph/workspace.toml --json

pragmagraph store-query .pragmagraph/graph.sqlite RuntimeGraph --json
pragmagraph store-search-explain .pragmagraph/graph.sqlite RuntimeGraph --json
pragmagraph store-health .pragmagraph/graph.sqlite --json
pragmagraph store-export .pragmagraph/graph.sqlite \
  --out .pragmagraph/exported-snapshot.json
```

Verify the full import/export/search loop:

```bash
pragmagraph store-round-trip .pragmagraph/snapshot.json \
  --store .pragmagraph/graph.sqlite \
  --query RuntimeGraph \
  --export-out .pragmagraph/exported-snapshot.json \
  --json
```

`store-search-explain` runs the same materialized-store query path as
`store-query` and reports the observed execution strategy, FTS availability,
candidate node IDs, omitted reasons, store identity/schema facts, and a
reproducible `store-query` command.
It is an explain surface over existing search, not a separate ranking engine.

`store-round-trip` imports a canonical JSON snapshot into the materialized
store, exports it back to canonical JSON, compares deterministic snapshot bytes,
and optionally includes the same search explanation facts for a query. It is a
local interchange proof for operators and CI jobs; it does not create a new
canonical store authority.

Older v1 stores remain readable without mutation. Migrate explicitly before
delta application:

```bash
pragmagraph store-migrate .pragmagraph/graph.sqlite --json
pragmagraph store-update .pragmagraph/graph.sqlite \
  .pragmagraph/snapshot.json --json
```

Run the local service against the store:

```bash
pragmagraph serve --store .pragmagraph/graph.sqlite
```

## Capability Rules

1. `StoreManifest` records backend name, schema version, snapshot schema,
   counts, source-ref count, FTS availability, and typed diagnostics.
2. `StoreCapabilityReport` advertises readable/writable/query/traversal/import
   support and unsupported modes.
3. Missing optional search support must be visible as typed diagnostics; it must
   not silently change query semantics.
4. Migrated SQLite stores select `direct_exact`, `indexed_trigram`, or
   `sql_canonical_scan`, then apply the same canonical scorer used by JSON.
   Candidate sets are never truncated before scoring.
5. `store-export` and `store-round-trip` must round-trip back to deterministic
   JSON snapshots.
6. Migrated-store query and traversal use normalized SQL rows and report
   `snapshot_deserialized=false`; readable v1 stores report an explicit
   `snapshot_fallback` with `migration_required`.

## Boundary

Materialized stores are caches over observed facts. They do not infer author
intent, architectural recommendations, memory records, summaries, or semantic
judgments. LLM-assisted retrieval and vector sidecars remain deferred until a
separate boundary decision accepts them as non-canonical sidecars.
