# PragmaGraph Package Docs

Status: semantic alpha

This directory holds the public package documentation for standalone
`pragmagraph`.

## Start Here

| If you want to... | Read |
| --- | --- |
| Install and run a first local graph | [`getting-started.md`](getting-started.md) |
| See the shortest end-to-end product loop | [`ten-minute-tour.md`](ten-minute-tour.md) and [`standalone-product-cycle.md`](standalone-product-cycle.md) |
| Understand storage, refresh, and workspace state | [`storage-interchange.md`](storage-interchange.md), [`refresh-operations.md`](refresh-operations.md), and [`workspace-mode.md`](workspace-mode.md) |
| Export or serve graph facts | [`report-mode.md`](report-mode.md), [`export-mode.md`](export-mode.md), and [`service-mode.md`](service-mode.md) |
| Hand graph data to GraphFakos or another viewer | [`viewer-contract.md`](viewer-contract.md) |
| Check proof and public claim boundaries | [`certification-readiness-matrix.md`](certification-readiness-matrix.md) |

## Command Guide

| Command family | Use it for | Public posture |
| --- | --- | --- |
| `quickstart` | first local run with config, workspace, store, and visual artifact | recommended |
| `investigate`, `repo-map`, `freshness` | day-to-day structural navigation | recommended |
| `demo-ui` | reopening the local visual graph from a workspace config | recommended |
| `ui-preview`, `viewer-*`, `graph-pack-*` | lower-level viewer and portability proofs | advanced |
| `serve`, `mcp-*`, `pragmagraph-server` | repeated local queries or MCP client wiring | advanced |
| `precise-import` | caller-provided precise facts, including native SCIP payloads when the optional extra is installed | advanced |

## Topic Map

- Local navigation: [`navigation-mode.md`](navigation-mode.md) plus the public
  `investigate` command and `pragmagraph.investigate` import root.
- Interchange and ingestion: [`graphify-interop.md`](graphify-interop.md),
  [`advanced-ingestion-and-interchange.md`](advanced-ingestion-and-interchange.md),
  and [`native-scip-ingestion.md`](native-scip-ingestion.md).
- Structural views: [`advanced-structural-views.md`](advanced-structural-views.md)
  and [`git-history-mode.md`](git-history-mode.md).
- UI and validation: [`ui-contracts.md`](ui-contracts.md),
  [`benchmarking.md`](benchmarking.md), and
  [`testing-and-validation.md`](testing-and-validation.md).
- Contributor workflow: [`engineering-patterns.md`](engineering-patterns.md),
  [`code-quality-enforcement.md`](code-quality-enforcement.md), and
  [`cleanup-workflow.md`](cleanup-workflow.md).

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

The `0.0.8rc1` semantic alpha defines a reproducible observed-fact graph contract:

1. immutable DTOs, JSON snapshots, local indexing, and deterministic query,
   traversal, report, and export helpers,
2. JSON and SQLite-backed store contracts plus workspace persistence and
   explicit refresh/profile/status helpers,
3. Graphify-shaped interop, optional native SCIP protobuf intake, and exact
   cross-repository symbol evidence,
4. topology, document-graph, query-plan, parser-support, and git-lineage
   surfaces,
5. certification packs, benchmark helpers, visual demo commands, and
   package-owned validation fixtures.

## Boundary shorthand

1. PragmaGraph is the third brain for static, observed, reproducible facts from
   code, docs, artifacts, and history.
2. Sophiagraph is the second brain for agent-owned memory: learned preferences,
   operator pins, summaries, decisions, and judgments.
3. Sophia may cite Pragma; Pragma never stores Sophia's judgments.
