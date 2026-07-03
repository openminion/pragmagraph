# PragmaGraph Storage Interchange And Search Spec

Date: 2026-07-02
Status: accepted and executed
Owner: PragmaGraph
Related:
[`../trackers/storage-interchange-and-search-2026-07-02-tracker.md`](../trackers/storage-interchange-and-search-2026-07-02-tracker.md),
[`../graphify-interop.md`](../graphify-interop.md),
[`../service-mode.md`](../service-mode.md),
[`../refresh-operations.md`](../refresh-operations.md),
[`../advanced-structural-views.md`](../advanced-structural-views.md)

## Purpose

Define the package-owned storage abstraction that lets PragmaGraph ingest
static code, docs, artifacts, and git facts once, then search and navigate
those facts through interchangeable local storage backends.

The core product loop is:

```text
files/docs/code/git
  -> PragmaGraph indexer
  -> canonical observed-fact snapshot
  -> materialized storage backend
  -> search, graph navigation, export, and agent query APIs
```

This spec was accepted for the package-local SQLite/JSON storage slice. It does
not approve version bumps, publishing, optional Kuzu/DuckDB/vector dependencies,
background refresh, hosted services, or LLM-derived graph facts.

## Current State

PragmaGraph currently ships:

1. immutable graph DTOs for observed facts,
2. deterministic JSON snapshot load/save,
3. local indexing from files, docs, code, config, and git overlays,
4. query, report, topology, document graph, lineage, and export helpers,
5. Graphify-shaped JSON import/export,
6. local query service over one loaded snapshot,
7. GraphFakos-backed UI preview over a snapshot.

The gap is storage shape:

1. JSON snapshots are portable but not a fast indexed working store.
2. Full-text search currently depends on in-memory scan/query helpers.
3. Graph traversal is bound to snapshot materialization.
4. Vector search has no explicit sidecar boundary.
5. Storage capabilities are not exposed through one backend-neutral contract.

## External Research Baseline

The storage plan is grounded in these current public systems:

| System | Relevant lesson | Fit for PragmaGraph |
| --- | --- | --- |
| SQLite FTS5 | SQLite's FTS5 module provides embedded full-text search over text collections. | Best default materialized local search layer for paths, labels, symbols, doc headings, and body text. |
| Kuzu | Kuzu is an embedded property graph database optimized for graph workloads. | Optional graph-native backend for larger traversal and path workloads after SQLite proves the contract. |
| DuckDB FTS | DuckDB offers an FTS extension and is strong for local analytical reporting. | Useful for optional report/benchmark exports, not the first graph store. |
| Zvec | Alibaba's Zvec is an in-process vector database with dense/sparse vectors, filtering, FTS, hybrid search, and durable local storage. | Strong candidate for an optional local vector sidecar, not canonical truth storage. |
| DashVector | Alibaba Cloud DashVector is a managed vector retrieval service built on Proxima. | Remote vector adapter reserve only; not a default standalone dependency. |
| LanceDB | LanceDB exposes local and remote vector-table APIs for embedding search. | Optional vector sidecar candidate when a concrete consumer needs it. |
| Milvus/Zilliz | Milvus/Zilliz target high-scale vector search and managed vector infrastructure. | Future remote/large-scale vector adapter reserve, outside the initial package default. |
| Graphify-style tools | Competitive code/doc graph tools emphasize fast queryable knowledge graphs for AI assistants. | PragmaGraph needs indexed search and provider interchange, not only portable snapshots. |
| Sourcegraph/SCIP-style code intelligence | Stable definitions/references are represented as structured code-intelligence facts. | Symbol/reference facts should remain observed graph facts and round-trip through every store. |

## Storage Authority Model

PragmaGraph must keep a clear split between canonical facts and materialized
indexes:

1. **Canonical artifact:** deterministic JSON `GraphSnapshot`.
2. **Default materialized store:** SQLite-backed indexed store.
3. **Optional graph store:** Kuzu-backed property graph store.
4. **Optional analytics store:** DuckDB export or report store.
5. **Optional vector sidecar:** Zvec or another vector backend linked by stable
   graph node ids.

Only the canonical snapshot defines package truth. Materialized stores must be
rebuildable from a snapshot or source root, and must export back to an
equivalent snapshot within the supported contract.

## Proposed Public Contract

Add a backend-neutral store protocol similar in spirit to:

```python
class GraphStore:
    def import_snapshot(self, snapshot: GraphSnapshot) -> StoreManifest: ...
    def export_snapshot(self) -> GraphSnapshot: ...
    def query(self, request: QueryRequest) -> QueryResult: ...
    def neighbors(self, node_id: str, *, depth: int = 1) -> NeighborhoodResult: ...
    def path(self, source_id: str, target_id: str) -> PathResult: ...
    def health(self) -> StoreHealth: ...
    def capabilities(self) -> StoreCapabilityReport: ...
```

The concrete names can change during implementation, but the contract must
carry these ideas:

1. every store imports and exports the canonical snapshot shape,
2. every store declares capabilities before a caller requests optional features,
3. every store returns typed diagnostics for unsupported modes,
4. every query result preserves provenance and omitted-count honesty,
5. every backend can be tested by the same conformance harness.

Use `StoreCapabilityReport` as the shared capability noun across PragmaGraph
and Sophiagraph planning docs so cross-package backend discussions do not drift
between near-synonyms.

## Store Manifest

Each materialized store should persist or return a manifest with:

1. store format version,
2. snapshot schema version,
3. snapshot hash,
4. indexer version,
5. namespace,
6. root path or redacted root identity,
7. node, edge, omitted, and text-document counts,
8. enabled indexes,
9. backend name and backend version,
10. creation time in UTC,
11. privacy posture,
12. vector sidecar linkage, when present.

## Backend Plan

### JSON Snapshot Store

Role: canonical portable interchange.

Required behavior:

1. preserves deterministic ordering,
2. rejects unsupported schema versions,
3. produces stable hashes for identical snapshots,
4. remains the fallback when no materialized backend exists.

### SQLite Materialized Store

Role: default local indexed store.

Recommended tables:

1. `snapshots`
2. `nodes`
3. `edges`
4. `omitted_diagnostics`
5. `source_refs`
6. `node_text_fts`
7. `edge_text_fts`, only if useful
8. `parser_provenance`
9. `store_manifest`

Recommended indexes:

1. node id,
2. node kind,
3. node label,
4. source path,
5. edge source id,
6. edge target id,
7. edge kind,
8. omitted reason,
9. parser id/version.

Search modes:

1. exact node id lookup,
2. path lookup,
3. kind-filtered lookup,
4. symbol/label search,
5. full-text search over node text and doc sections,
6. graph neighborhood,
7. shortest path where cheap and deterministic,
8. omitted diagnostics search.

### Kuzu Graph Store

Role: optional embedded graph-native backend.

Entry condition:

1. SQLite store contract lands,
2. conformance tests prove snapshot round-trip behavior,
3. traversal benchmarks show a real need.

Kuzu must stay optional and lazy-imported. Missing Kuzu must produce a typed
capability error, not a silent fallback that changes results.

### DuckDB Analytics Store

Role: optional report and benchmark backend.

DuckDB should not become the primary graph store in this lane. It is useful for:

1. aggregate reports,
2. benchmark summaries,
3. time-series snapshot comparisons,
4. exportable analytical tables.

### Vector Sidecar Store

Role: optional semantic retrieval acceleration linked to observed facts.

Candidate local backend: Zvec.

Candidate remote backends: DashVector, LanceDB, Milvus/Zilliz.

Hard boundary:

1. vectors are sidecar indexes, not canonical graph facts,
2. embeddings must never create new graph edges by themselves,
3. vector hits must cite graph node ids and source refs,
4. embedding model, dimension, vector space, source hash, and created time must
   be explicit,
5. vector sidecars must be rebuildable or declared stale when graph facts
   change,
6. vector sidecar export must be opt-in because vectors can be large and may
   encode sensitive content.

The vector sidecar may improve ranking and recall, but it must not widen
PragmaGraph into Sophia-style judgment or LLM-owned interpretation.

## Import And Export Requirements

Every storage backend must support at least one of:

1. import from `GraphSnapshot`,
2. export to `GraphSnapshot`,
3. typed diagnostic explaining why the operation is unsupported.

The default supported stores must satisfy full round-trip:

```text
snapshot.json -> store -> snapshot.json
```

Acceptance requires:

1. stable node ids,
2. stable edge ids,
3. stable omitted diagnostics,
4. stable source refs,
5. stable stats or documented store-specific stats,
6. stable privacy posture,
7. typed diagnostics for lossy fields.

## CLI Shape

Candidate commands:

```bash
pragmagraph store-import snapshot.json --backend sqlite --out .pragmagraph/index.sqlite
pragmagraph store-export .pragmagraph/index.sqlite --out snapshot.roundtrip.json
pragmagraph store-health .pragmagraph/index.sqlite --json
pragmagraph store-query .pragmagraph/index.sqlite RuntimeGraph --json
pragmagraph store-neighborhood .pragmagraph/index.sqlite node-id --depth 2 --json
pragmagraph store-path .pragmagraph/index.sqlite source-id target-id --json
pragmagraph vector-sidecar-build snapshot.json --backend zvec --out .pragmagraph/vectors.zvec
pragmagraph vector-sidecar-search .pragmagraph/vectors.zvec "runtime config" --json
```

Command names can be refined during acceptance, but the user-facing intent
should stay stable:

1. import/export between snapshot and store,
2. inspect store health,
3. query through a store,
4. build optional vector sidecar,
5. search optional vector sidecar with explicit capability metadata.

## Search Semantics

PragmaGraph search should support these query families:

1. lexical text search,
2. exact id lookup,
3. path search,
4. symbol/label search,
5. doc-section search,
6. graph-neighborhood search,
7. path search between two facts,
8. changed-fact search across git overlays,
9. omitted diagnostic search,
10. optional vector sidecar retrieval.

Each result should include:

1. result id,
2. score or ordering reason,
3. matched fields,
4. source refs,
5. graph node/edge refs,
6. backend capability used,
7. omitted count when limits apply.

## Privacy And Portability

Materialized stores must not leak more than the source snapshot by default.

Rules:

1. full paths follow the same redaction posture as snapshots,
2. git identity posture remains explicit,
3. vector sidecars are not exported by default,
4. store manifests must record whether vectors include raw text-derived
   embeddings,
5. remote vector adapters are opt-in and must never run during default package
   checks.

## Non-Goals

This spec does not approve:

1. hosted PragmaGraph services,
2. background daemons or automatic watchers,
3. LLM-generated semantic graph edges,
4. vector search as canonical storage,
5. required Kuzu, DuckDB, Zvec, LanceDB, DashVector, Milvus, or Neo4j
   dependencies,
6. replacing JSON snapshots,
7. changing the Graphify interop contract without a dedicated compatibility
   row.

## Validation Expectations

The implementation tracker must require:

1. JSON round-trip conformance tests,
2. SQLite import/export conformance tests,
3. query parity tests between snapshot and SQLite for supported query modes,
4. typed unsupported-capability tests,
5. deterministic store manifest tests,
6. optional-backend missing-dependency tests,
7. vector sidecar boundary tests when sidecar work is accepted,
8. package `make check`,
9. package `make release-check` when public import roots or packaging change.

## Open Questions

1. Should SQLite become the default `serve` backend when a materialized index is
   present?
2. Should vector sidecar search return raw similarity scores or normalized
   package scores?
3. Should Kuzu import/export live in the core package extra or a separate
   adapter package?
4. Should DuckDB exports be queryable through the same `GraphStore` protocol or
   remain report-only?
5. Should vector sidecar metadata be included in normal snapshot stats or a
   separate manifest only?
