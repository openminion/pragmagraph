# pragmagraph API Compatibility Policy

Owner: `pragmagraph`
Status: `alpha`
Scope: stable import-root and versioning policy for external `pragmagraph`
consumers during the semantic-alpha phase

## Purpose

Define what external consumers can rely on while `pragmagraph` is a small
semantic alpha.

## Stable import roots

External consumers should treat these import roots as the supported public API:

- `pragmagraph`
- `pragmagraph.contracts`
- `pragmagraph.models`
- `pragmagraph.query`
- `pragmagraph.storage`
- `pragmagraph.adapters`
- `pragmagraph.bench`
- `pragmagraph.portability`
- `pragmagraph.parsers`
- `pragmagraph.export`
- `pragmagraph.graphify`
- `pragmagraph.report`
- `pragmagraph.refresh`
- `pragmagraph.operations`
- `pragmagraph.navigation`
- `pragmagraph.interchange`
- `pragmagraph.topology`
- `pragmagraph.docgraph`
- `pragmagraph.planner`
- `pragmagraph.certification`
- `pragmagraph.lineage`
- `pragmagraph.parser_support`
- `pragmagraph.security`
- `pragmagraph.service`
- `pragmagraph.ui`
- `pragmagraph.workspace`

The top-level `pragmagraph` package is the preferred entrypoint for package
metadata and smoke validation.

## Stable top-level exports

The following top-level exports are part of the current public contract:

- `pragmagraph.__version__`
- `pragmagraph.PACKAGE_STATUS`
- `pragmagraph.STABLE_IMPORT_ROOTS`
- semantic DTOs such as `GraphNode`, `GraphEdge`, `GraphSnapshot`,
  `SourceRef`, `QueryRequest`, and `QueryResult`
- snapshot helpers `load_snapshot`, `save_snapshot`, and `stable_dumps`
- local indexer helper `index_path`
- benchmark helpers `benchmark_root` and `render_markdown_benchmark`
- graph export helpers `render_dot`, `render_mermaid`, and
  `render_graph_export`
- Graphify-shaped JSON interop helpers `to_graphify_payload`,
  `snapshot_from_graphify_payload`, and `GRAPHIFY_INTEROP_FORMAT`
- structural report helpers `build_report` and `render_markdown_report`
- compact navigation helpers `build_repo_map`, `render_markdown_repo_map`, and
  `render_compact_handoff`
- stable symbol/reference interchange helper `build_symbol_reference_bundle`
- precise-fact interchange helpers under `pragmagraph.interchange`, including
  `snapshot_from_compiler_facts`, `snapshot_to_scip_json`, and
  `snapshot_from_scip_json`; optional native SCIP contracts and helpers include
  `NativeScipImport`, `ScipIngestionReport`, `ScipFreshness`,
  `ScipLossReport`, `load_native_scip`, `snapshot_from_scip_protobuf`,
  `merge_precise_snapshot`, and `native_scip_available`
- topology and document-graph helpers `build_topology_summary` and
  `build_doc_graph_summary`
- query-plan evidence helper `explain_query_plan`
- certification/privacy helpers `build_certification_pack` and
  `build_privacy_profile`
- git lineage helper `build_git_lineage`
- parser support helper `build_parser_support_matrix`
- refresh helpers `refresh_snapshot`, `diff_snapshots`, and `build_ci_delta`
- structural navigation helpers `reverse_imports`, `reverse_dependencies`,
  `backlinks`, and `impact`
- service contracts `ServiceRequest`, `ServiceResponse`, and `LocalQueryService`
- workspace contracts `WorkspaceMetadata`, `WorkspacePaths`,
  `WorkspaceStatusView`, `WorkspaceRefreshResult`, and helpers such as
  `initialize_workspace`, `refresh_workspace`, `load_workspace_metadata`, and
  `load_workspace_status`, plus `WorkspaceRoot` and `index_multi_root`
- export projection helpers `project_snapshot` and `ExportProjection`
- typed UI boundary contracts such as `UiTransportBoundary`,
  `UiScreenDefinition`, and `build_ui_screen_manifest`
- parser/scope DTOs such as `ParserDiagnostic`, `ParserResult`,
  `RefreshManifest`, `RefreshResult`, `RefreshPathChange`,
  `SnapshotStructuralDelta`, and `QueryExplanation`
- report DTOs such as `GraphReport`, `GraphReportSummary`,
  `GraphReportNode`, `GraphReportFinding`, and `GraphReportDependency`

Query helpers live under `pragmagraph.query`; they are intentionally not
re-exported as top-level names so the `pragmagraph.query` import root remains a
module.

## Snapshot contract

`SCHEMA_VERSION = "pragmagraph.snapshot.v1alpha1"` is the current JSON snapshot
schema. The schema is alpha but deterministic: snapshots are JSON objects with
stable `nodes`, `edges`, `omitted`, and `stats` fields. Future schema changes
must either preserve load compatibility or fail with typed package errors.

## Versioning posture

`pragmagraph` is currently `0.x` software.

That means:

1. additive API changes are preferred,
2. breaking changes are still possible,
3. breaking changes must be called out in release notes and package docs,
4. stable import roots should not be moved casually even during `0.x`.

## Deprecation policy

When a public symbol or import path needs to change:

1. prefer an additive replacement first,
2. document the new path in `README.md`,
3. keep the old path available for at least one `0.x` release when practical,
4. remove only after the deprecation is documented in release notes.

If a safety or correctness issue requires immediate removal, the release notes
must say so explicitly.

## Compatibility tests

Public-contract confidence should be enforced by tests that cover:

1. import-root availability,
2. public top-level export availability,
3. version agreement between `pyproject.toml` and `pragmagraph.__version__`,
4. package independence from OpenMinion imports,
5. semantic smoke behavior,
6. release/install smoke for built artifacts,
7. deterministic report JSON/Markdown behavior over fixture snapshots,
8. deterministic DOT/Mermaid export behavior over fixture snapshots,
9. Graphify-shaped JSON import/export behavior over fixture snapshots,
10. mixed-language parser coverage and explicit optional-parser diagnostics,
11. incremental refresh manifest/delta determinism over repeated refreshes,
12. benchmark behavior over the package-owned medium fixture,
13. deterministic stdio service behavior for snapshot-backed and root-backed
    repeated-request sessions,
14. deterministic workspace init/status/refresh behavior and
    `serve --workspace` startup,
15. deterministic compact repo-map and handoff rendering,
16. deterministic symbol/reference interchange, bounded native SCIP intake,
    topology, document-graph,
    query-plan, git-lineage, parser-support, and certification behavior.

## Non-goals

This policy does not promise:

1. host-framework orchestration semantics,
2. graph-database storage behavior,
3. Graphify runtime API wrapping or hosted Graphify artifact mapping,
4. semantic inference of facts, labels, relations, or summaries from prose,
5. compatibility for undocumented import paths.
