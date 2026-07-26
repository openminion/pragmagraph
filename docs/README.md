# PragmaGraph Package Docs

Status: semantic alpha

This directory holds the public package documentation for standalone
`pragmagraph`.

## Package-local references

- [`getting-started.md`](getting-started.md) gives the
  package-local bootstrap and execution summary for contributors and automation.
- [`ten-minute-tour.md`](ten-minute-tour.md) gives the shortest public
  standalone path through workspace config, visual preview, store explain, and
  certification output.
- [`standalone-product-cycle.md`](standalone-product-cycle.md) gives the
  public package loop for workbench navigation, delta review, graph packs,
  storage/search backend inspection, and MCP client snippets.
- [`engineering-patterns.md`](engineering-patterns.md)
  summarizes the package-local engineering and boundary rules for contributors.
- [`code-quality-enforcement.md`](code-quality-enforcement.md)
  summarizes the active public quality gates and validation posture.
- [`cleanup-workflow.md`](cleanup-workflow.md) defines the live-inventory,
  per-file-ledger, and closeout process for broad maintainability work.
- [`testing-and-validation.md`](testing-and-validation.md)
  records the package-local install, smoke, test, lint, and release-check
  flow.
- [`report-mode.md`](report-mode.md) records the structural
  report contract and CLI shape.
- [`export-mode.md`](export-mode.md) records DOT/Mermaid
  text export contracts and CLI shape.
- [`service-mode.md`](service-mode.md) records the local
  service request/response contract.
- [`storage-interchange.md`](storage-interchange.md) records the
  canonical snapshot, JSON store, SQLite materialized store, and vector
  sidecar boundary.
- [`workspace-mode.md`](workspace-mode.md) records the
  package-owned persistent local workspace contract.
- [`refresh-operations.md`](refresh-operations.md) records
  the package-owned explicit refresh/profile/status surface.
- [`navigation-mode.md`](navigation-mode.md) records the
  compact repo-map and handoff surfaces for fast local graph orientation.
- [`ui-contracts.md`](ui-contracts.md) records the
  package-owned `pragmagraph.ui` boundary for the future OpenMinion workbench
  surface.
- [`benchmarking.md`](benchmarking.md) records the
  package-owned benchmark surface and repo-local regression fixture policy.
- [`graphify-interop.md`](graphify-interop.md) records the
  deterministic Graphify-shaped JSON import/export contract.
- [`viewer-contract.md`](viewer-contract.md) records the
  provider-neutral viewer envelope, scale-fixture commands, and GraphFakos
  handoff boundary.
- [`git-history-mode.md`](git-history-mode.md) records the
  local git-overlay contract, privacy posture, and CLI shape.
- [`advanced-structural-views.md`](advanced-structural-views.md)
  records symbol/reference interchange, topology, document-graph, query-plan,
  git-lineage, parser-support, and certification helper surfaces.
- [`advanced-ingestion-and-interchange.md`](advanced-ingestion-and-interchange.md)
  records multi-root composition, artifact indexing, CI delta, precise-fact
  interchange, exact cross-repository SCIP resolution, query pagination,
  export redaction, and read-only MCP resources.
- [`native-scip-ingestion.md`](native-scip-ingestion.md) records
  optional native SCIP protobuf intake, exact merge/freshness rules, and the
  certified producer boundary.
- [`certification-readiness-matrix.md`](certification-readiness-matrix.md)
  records the current standalone and OpenMinion proof targets for the public
  package surface.

## Package-local code/docs boundaries

1. `README.md` is the public package contract and install surface.
2. `API_COMPATIBILITY.md` records the supported public import roots and
   top-level export policy.
3. The Source Tree Owner Map reference explains the source-tree owner map and
   public-vs-repo-local boundary.
4. `CHANGELOG.md` records package-facing release notes.
5. `CODE_QUALITY.md` summarizes the public contributor code-quality rules.
6. `RELEASING.md` records the package-local release and PyPI publish flow.
7. `scripts/release_check.py` is the canonical package release smoke entrypoint.

## Repository-local but not package API

1. `tests/fixtures/repos/` holds regression fixtures used by benchmarks,
   examples, and deterministic package tests.
2. `tests/contracts/` holds OpenMinion-facing contract snapshots used by
   adapter and provider-swap validation.
3. Host-framework planning and runtime-integration docs stay outside this
   package-local docs directory.

## Public package stance

The `0.0.7` semantic alpha defines the current public package contract:
immutable DTOs, JSON snapshots, local indexing, deterministic
query/traversal/report/export helpers, JSON and SQLite-backed store contracts,
compact navigation maps,
Graphify-shaped interop, package-local service and UI boundary contracts,
explicit refresh/profile/status helpers, workspace persistence helpers,
git-aware provenance overlays and path lineage, symbol/reference interchange,
optional native SCIP protobuf intake,
topology and document-graph summaries, query-plan evidence, parser-support
metadata, certification packs with Markdown output, benchmark helpers,
package-owned visual demo commands, and package-owned validation fixtures.

## Boundary shorthand

1. PragmaGraph is the third brain for static, observed, reproducible facts from
   code, docs, artifacts, and history.
2. Sophiagraph is the second brain for agent-owned memory: learned preferences,
   operator pins, summaries, decisions, and judgments.
3. Sophia may cite Pragma; Pragma never stores Sophia's judgments.
