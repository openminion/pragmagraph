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
export, graphify, report, refresh, navigation, interchange, topology, docgraph,
planner, certification, lineage, parser_support, investigate, security,
service, workspace, and `pragmagraph.ui`.

## Source-tree owner map

1. `contracts/` owns schema/version constants and typed package errors.
2. `models/` owns immutable DTOs.
3. `adapters/` owns local indexing from source roots into snapshots, including
   git-history overlays and bounded artifact-specific fact extraction.
4. `query/` owns deterministic search, explain, neighborhood, path, health,
   and git-aware lookup helpers.
5. `storage/` owns snapshot load/save and stable JSON encoding.
6. `report/`, `export/`, and `graphify/` own derived structural views over
   snapshots, including structural git-overlay summaries and non-mutating
   export redaction profiles.
7. `refresh/` owns content-hash manifest, refresh behavior, and CI-facing
   canonical snapshot deltas.
8. `operations.py` owns explicit refresh planning, saved invocation profiles,
   persisted status ledgers, and repeatable local ingest runs.
9. `navigation/` owns compact repo-map and handoff views over observed
   snapshots.
10. `investigate/` owns guided graph-inspection bundles that compose query,
   neighborhood, path, freshness, and next-command facts without owning new
   indexing, storage, or semantic ranking.
11. `interchange/`, `topology/`, `docgraph/`, `planner/`,
   `certification/`, `lineage/`, and `parser_support/` own advanced
   structural views over observed snapshots. `interchange/` also owns the SCIP
   JSON subset, optional native SCIP protobuf intake, and caller-fed exact
   compiler/LSP fact bridge. `interchange/scip_symbols.py` owns grammar-aware
   complete SCIP identity validation; query-time code must not reimplement it.
12. `workspace/` owns the persistent local workspace directory contract,
   explicit workspace lifecycle helpers, deterministic multi-root overlays,
   named canonical-snapshot composition, and exact cross-root resolution.
   `workspace/cli.py` owns both multi-root command registrations so the root CLI
   remains an orchestrator.
13. `service/` owns the local repeated-query service boundary. `server/` owns
   the bounded MCP transport, tool registry, and read-only resource registry.
14. `ui/` owns typed UI contracts, the PragmaGraph-to-GraphFakos adapter, and
   package CLI preview wiring. `ui/__init__.py` remains the stable UI import
   seam, `ui/contracts.py` owns typed route and transport-boundary contracts,
   `ui/local_server.py` remains the stable local-viewer compatibility seam,
   `preview.py` is the stable preview façade,
   `preview_types.py` owns typed request/result contracts, and
   `preview_inputs.py` owns preview request parsing plus snapshot-loading and
   GraphFakos bridge helpers. Shared viewer shell, local server behavior,
   static export, and reusable viewer assertions belong to GraphFakos.

## Repo-local but not public API

1. `tests/fixtures/repos/` holds regression fixtures for package tests and
   benchmarks.
2. `tests/contracts/` holds OpenMinion-facing contract snapshots for adapter
   and provider validation.
3. `examples/` are usage demos, not additional stability guarantees beyond the
   documented public surface.
4. `scripts/validate_quality_patterns.py` and `scripts/baselines/` own the
   package-local structural quality ratchets used by `make validate-patterns`
   and `make check`.
