# PragmaGraph Source Tree Owner Map

Status: semantic alpha

Purpose: explain the `pragmagraph` source-tree owners without treating deep
imports as blanket public promises.

## Public contract

The public alpha surface is documented in:

1. `README.md`
2. `API_COMPATIBILITY.md`
3. `docs/`

The preferred entrypoint is `pragmagraph`, with additional stable import roots
for contracts, models, query, storage, adapters, bench, portability, parsers,
export, graphify, report, refresh, security, service, workspace, and
`pragmagraph.ui`.

## Source-tree owner map

1. `contracts/` owns schema/version constants and typed package errors.
2. `models/` owns immutable DTOs.
3. `adapters/` owns local indexing from source roots into snapshots, including
   git-history overlays.
4. `query/` owns deterministic search, explain, neighborhood, path, health,
   and git-aware lookup helpers.
5. `storage/` owns snapshot load/save and stable JSON encoding.
6. `report/`, `export/`, and `graphify/` own derived structural views over
   snapshots, including structural git-overlay summaries.
7. `refresh/` owns content-hash manifest and refresh behavior.
8. `operations.py` owns explicit refresh planning, saved invocation profiles,
   persisted status ledgers, and repeatable local ingest runs.
9. `workspace/` owns the persistent local workspace directory contract and
   explicit workspace lifecycle helpers.
10. `service/` owns the local repeated-query service boundary.
11. `ui/` owns typed UI contracts, the PragmaGraph-to-GraphFakos adapter, and
   package CLI preview wiring. Shared viewer shell, local server behavior,
   static export, and reusable viewer assertions belong to GraphFakos.

## Repo-local but not public API

1. `tests/fixtures/repos/` holds regression fixtures for package tests and
   benchmarks.
2. `tests/contracts/` holds OpenMinion-facing contract snapshots for adapter
   and provider validation.
3. `examples/` are usage demos, not additional stability guarantees beyond the
   documented public surface.
