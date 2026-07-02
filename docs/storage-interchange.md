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
pragmagraph store-import .pragmagraph/snapshot.json \
  --out .pragmagraph/graph.sqlite
```

Query, inspect, and export the store:

```bash
pragmagraph store-query .pragmagraph/graph.sqlite RuntimeGraph --json
pragmagraph store-health .pragmagraph/graph.sqlite --json
pragmagraph store-export .pragmagraph/graph.sqlite \
  --out .pragmagraph/exported-snapshot.json
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
4. SQLite FTS5 is used when available. When unavailable, `SQLiteGraphStore`
   keeps query parity by falling back to deterministic SQL scan plus snapshot
   query ranking.
5. `store-export` must round-trip back to a deterministic JSON snapshot.

## Boundary

Materialized stores are caches over observed facts. They do not infer author
intent, architectural recommendations, memory records, summaries, or semantic
judgments. LLM-assisted retrieval and vector sidecars remain deferred until a
separate boundary decision accepts them as non-canonical sidecars.
