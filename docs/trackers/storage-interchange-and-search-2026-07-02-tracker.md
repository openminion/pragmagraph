# PragmaGraph Storage Interchange And Search Tracker

Date: 2026-07-02
Status: done
Owner: PragmaGraph
Related:
[`../specs/storage-interchange-and-search-2026-07-02-spec.md`](../specs/storage-interchange-and-search-2026-07-02-spec.md),
[`../service-mode.md`](../service-mode.md),
[`../graphify-interop.md`](../graphify-interop.md),
[`../refresh-operations.md`](../refresh-operations.md)

## Purpose

Track the package work required to make PragmaGraph storage interchangeable and
searchable through materialized stores while preserving the canonical
observed-fact snapshot contract.

This tracker was accepted and executed for the package-local JSON/SQLite
storage slice. Deferred optional graph, analytics, and vector backends remain
reserved behind their entry conditions.

## Review State

Current state:

1. `12/12` active rows are complete.
2. `0/12` active rows remain `todo`.
3. no version change was made.
4. no optional backend dependency was added.
5. optional Kuzu, DuckDB, Zvec, DashVector, LanceDB, Milvus, and Zilliz rows
   remain deferred or reserved.

## Candidate Board

| ID | Priority | Class | Status | Task | Why it matters | Entry condition |
| --- | --- | --- | --- | --- | --- | --- |
| `PGSIS-00` | P0 | review gate | `done` | Accept or revise the storage interchange and search scope. | Prevents storage work from mixing canonical facts, materialized indexes, and vector sidecars. | Accepted JSON/SQLite slice only; no version bump, optional dependency, hosted service, background refresh, or vector sidecar approved. |
| `PGSIS-01` | P0 | contract | `done` | Define `GraphStore`, `StoreManifest`, `StoreCapabilityReport`, and typed store errors. | Every backend needs the same import/export/query/health shape. | Landed in `src/pragmagraph/storage/backends.py`; exported through `pragmagraph.storage`. |
| `PGSIS-02` | P0 | conformance | `done` | Add store conformance fixtures for snapshot import/export round-trip, query parity, capability reporting, and unsupported modes. | Backends should prove behavior through one shared harness. | `tests/test_storage_interchange.py` covers JSON oracle parity, SQLite round-trip, capability reporting, unsupported vector modes, CLI, service, and Graphify interop. |
| `PGSIS-03` | P0 | backend | `done` | Implement `JsonSnapshotStore` over existing deterministic snapshot load/save. | Establishes the canonical backend and test oracle before materialized stores. | `JsonSnapshotStore` wraps canonical snapshots and is asserted as the query oracle in `tests/test_storage_interchange.py`. |
| `PGSIS-04` | P0 | backend | `done` | Implement `SQLiteGraphStore` with node, edge, omitted, source-ref, manifest, and FTS tables. | Gives PragmaGraph fast local search without hosted services or heavy default dependencies. | `SQLiteGraphStore` persists snapshot, nodes, edges, omitted diagnostics, source refs, manifest, and FTS5 table when available; FTS absence returns typed capability diagnostics. |
| `PGSIS-05` | P0 | search | `done` | Route lexical, path, symbol, doc-section, omitted, neighborhood, and path queries through the store contract. | Makes storage useful for human UI, MCP, and OpenMinion-style query consumers. | Store `query`, `neighborhood`, `path`, `health`, and export methods preserve snapshot parity with store diagnostics. |
| `PGSIS-06` | P1 | CLI | `done` | Add import/export/health/query CLI commands for store-backed workflows. | Users and agents need direct commands, not only Python imports. | Added `store-import`, `store-export`, `store-health`, `store-query`, `store-neighborhood`, and `store-path`. |
| `PGSIS-07` | P1 | service | `done` | Teach local query service to use a store backend when configured. | Keeps long-lived service mode aligned with the new storage abstraction. | Added service `store` startup mode, `LocalQueryService.from_store_path`, `serve --store`, and store metadata in capabilities/health. |
| `PGSIS-08` | P1 | interop | `done` | Verify Graphify-shaped import/export against store-backed snapshots. | Storage interchange must not break the provider-swap story. | `test_graphify_payload_round_trips_through_sqlite_store` verifies store-backed Graphify node/edge/omitted parity. |
| `PGSIS-09` | P1 | benchmark | `done` | Add storage benchmark reports for JSON scan vs SQLite store query families. | Backend choice should be based on measured search/traversal value. | `benchmark_root` now reports `json_query`, `sqlite_import`, and `sqlite_query`; `tests/test_bench.py` updated. |
| `PGSIS-10` | P1 | docs | `done` | Document canonical snapshot vs materialized stores vs vector sidecars. | Public users need to understand which artifact is portable truth. | Added `docs/storage-interchange.md`; updated `README.md` and `docs/README.md`. |
| `PGSIS-CQ` | P0 | closeout | `done` | Run package validation and reconcile follow-up owners. | Prevents hidden backlog and untested optional-backend claims. | Focused tests and targeted Ruff pass; full `make check` and `make release-check` evidence recorded below. |

## Evidence

1. `PGSIS-01` through `PGSIS-07`: `src/pragmagraph/storage/backends.py`,
   `src/pragmagraph/service/runtime.py`, `src/pragmagraph/service/models.py`,
   `src/pragmagraph/service/constants.py`, and `src/pragmagraph/__main__.py`.
2. `PGSIS-02`, `PGSIS-08`: `tests/test_storage_interchange.py`.
3. `PGSIS-09`: `src/pragmagraph/bench/__init__.py` and
   `tests/test_bench.py`.
4. `PGSIS-10`: `README.md`, `docs/README.md`, and
   `docs/storage-interchange.md`.
5. Focused validation:
   `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:../graphfakos/src python3.11 -m pytest tests/test_storage_interchange.py tests/test_service.py tests/test_bench.py`
   passed with `17 passed`.
6. Targeted lint:
   `PYTHONDONTWRITEBYTECODE=1 ruff check src/pragmagraph/storage src/pragmagraph/service src/pragmagraph/bench src/pragmagraph/__main__.py tests/test_storage_interchange.py tests/test_bench.py`
   passed.
7. Package validation:
   `PYTHONDONTWRITEBYTECODE=1 make check` passed with `90 passed`.
8. Release validation:
   `PYTHONDONTWRITEBYTECODE=1 make release-check` passed; it built
   `pragmagraph-0.0.3`, ran Twine checks, installed the wheel with
   GraphFakos, ran `pragmagraph-smoke --json`, and replayed the UI artifact.
9. Workspace closeout gates:
   `cd ../openminion && .venv/bin/python3.11 -m ruff check .` passed, and
   `cd ../openminion && make lint` passed.
10. Post-authoring cleanup:
    `src/pragmagraph/storage/backends.py` was trimmed from 678 to 663 LOC by
    collapsing repetitive DTO serialization into shallow dataclass
    serialization; `PYTHONDONTWRITEBYTECODE=1 make check` passed with
    `90 passed`.

## Deferred And Reserved Rows

| ID | Class | Status | Task | Entry condition |
| --- | --- | --- | --- | --- |
| `PGSIS-F01` | optional graph backend | `deferred` | Add Kuzu-backed graph store. | SQLite store lands, traversal benchmarks show need, and `pragmagraph[kuzu]` optional dependency policy is accepted. |
| `PGSIS-F02` | optional analytics backend | `deferred` | Add DuckDB-backed analytics/report export. | Reporting workload proves value beyond existing deterministic reports. |
| `PGSIS-F03` | vector sidecar | `deferred` | Add Zvec-backed local vector sidecar. | Separate acceptance confirms vector sidecar remains non-canonical and opt-in. |
| `PGSIS-F04` | remote vector adapter | `deferred` | Add DashVector, LanceDB, Milvus, or Zilliz adapter. | A real consumer requests remote vector search and privacy/export policy is accepted. |

## Boundary Rules

1. JSON snapshots remain canonical package truth.
2. Materialized stores are rebuildable indexes or caches over canonical facts.
3. Store import/export must preserve observed facts or return typed diagnostics.
4. Vector sidecars never create graph truth.
5. Missing optional backends return typed capability errors.
6. No background watchers, hosted services, or automatic refresh triggers are
   approved by this tracker.
7. No LLM-derived graph edges are approved by this tracker.

## Validation Checklist

Implementation closeout must include:

1. `PYTHONDONTWRITEBYTECODE=1 make check`,
2. `PYTHONDONTWRITEBYTECODE=1 make release-check` when public imports,
   packaging, or extras change,
3. focused conformance tests for every accepted backend,
4. missing optional dependency tests,
5. query parity tests against the JSON snapshot oracle,
6. manifest determinism tests,
7. docs examples that use repo-relative paths only.

## Research Notes

1. SQLite FTS5 is the default candidate for local full-text indexing because it
   is embedded and matches the package-local/no-service posture.
2. Kuzu is the graph-native optional candidate for larger traversal workloads.
3. Zvec is the strongest local-first vector sidecar candidate because it is
   in-process and supports dense/sparse vectors, filtering, FTS, and hybrid
   search.
4. DashVector, LanceDB, Milvus, and Zilliz stay remote or optional-vector
   reserves until a concrete consumer needs them.
5. These research notes intentionally duplicate the Sophiagraph storage
   retrieval tracker at package-local altitude; update both package docs when
   the external storage baseline changes.
