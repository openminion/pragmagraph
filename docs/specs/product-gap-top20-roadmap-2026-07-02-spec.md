# PragmaGraph Product Gap Top 20 Roadmap Spec

Date: 2026-07-02
Status: draft discussion, not executable
Owner: PragmaGraph
Related:
[`../trackers/product-gap-top20-roadmap-2026-07-02-tracker.md`](../trackers/product-gap-top20-roadmap-2026-07-02-tracker.md),
[`../storage-interchange.md`](../storage-interchange.md),
[`../advanced-structural-views.md`](../advanced-structural-views.md),
[`../service-mode.md`](../service-mode.md),
[`../ui-contracts.md`](../ui-contracts.md),
[`../graphify-interop.md`](../graphify-interop.md),
[`../git-history-mode.md`](../git-history-mode.md)

## Purpose

Collect the next twenty PragmaGraph product gaps into one review-only roadmap
so future work can be promoted deliberately instead of creating overlapping
gap catalogs.

This spec does not start implementation. A row becomes executable only after a
follow-up tracker accepts a bounded slice, names validation, and restates the
PragmaGraph boundary:

```text
source files / docs / artifacts / git
  -> observed static facts
  -> canonical snapshot
  -> optional materialized stores or sidecars
  -> search, navigation, export, UI, and MCP-facing query surfaces
```

## Research Baseline

The roadmap is grounded in public product and open-source patterns that matter
for code, document, graph, retrieval, and agent access workflows.

| Source | Public reference | Lesson for PragmaGraph |
| --- | --- | --- |
| SCIP | <https://scip-code.org/> and <https://github.com/scip-code/scip> | Code-intelligence tools benefit from a language-agnostic index format for definitions, references, implementations, and navigation. |
| Tree-sitter | <https://tree-sitter.github.io/tree-sitter/> | Incremental concrete syntax trees can improve parser coverage while remaining dependency-scoped. |
| Kythe | <https://kythe.io/docs/> | Stable cross-reference schemas need anchors, facts, edges, and language-neutral node identity. |
| CodeQL | <https://codeql.github.com/docs/> | Treating code as queryable data is valuable, but PragmaGraph should ingest only observed query results or facts, not infer security meaning. |
| Semgrep | <https://docs.semgrep.dev/> | Rule-based findings can be represented as reproducible diagnostics with source ranges and rule ids. |
| Microsoft GraphRAG | <https://microsoft.github.io/graphrag/> | Graph-backed retrieval is useful, but LLM-extracted graph construction belongs outside PragmaGraph unless the boundary is explicitly widened. |
| LlamaIndex Property Graph | <https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/> | Property-graph construction and querying are common expectations for agent knowledge systems. PragmaGraph should satisfy the structural subset. |
| SQLite FTS5 | <https://www.sqlite.org/fts5.html> | Embedded full-text search is the right default local search baseline. |
| Kuzu | <https://kuzudb.github.io/docs/> | Embedded graph storage is a credible optional backend for larger traversal workloads. |
| LanceDB | <https://docs.lancedb.com/> | Local and remote vector tables are useful as optional sidecars, not canonical graph truth. |
| Milvus | <https://milvus.io/docs> | High-scale vector stores belong behind optional remote or large-workload adapters. |
| Qdrant | <https://qdrant.tech/documentation/> | Filtered vector retrieval and payload metadata are relevant to future sidecars. |
| Chroma | <https://docs.trychroma.com/docs/overview/introduction> | Developer-friendly vector and metadata search raises user expectations for simple local retrieval setup. |
| DashVector | <https://www.alibabacloud.com/help/en/vrs/latest/what-is-vector-retrieval-service> | Managed vector retrieval is a hosted reserve, not a default standalone dependency. |
| Model Context Protocol | <https://modelcontextprotocol.io/specification/2025-06-18> | Agent-facing graph tools should expose resources, tools, and capability metadata through a stable protocol shape. |

## Boundary Rules

1. PragmaGraph owns reproducible static facts from files, docs, artifacts, and
   git history.
2. PragmaGraph may store observed diagnostics from tools such as Semgrep,
   CodeQL, tests, or linters when source ranges and command provenance are
   explicit.
3. PragmaGraph must not infer author intent, architectural meaning, risk,
   memory preference, or recommendation.
4. JSON snapshots remain canonical truth; materialized stores and vector
   sidecars are rebuildable indexes.
5. Optional parser, graph, analytics, vector, hosted, and MCP dependencies must
   stay lazy-imported and capability-reported.
6. Background watchers, hosted services, vector sidecars, and LLM-derived graph
   facts require separate scope acceptance before implementation.

## Top 20 Roadmap Items

| Rank | Item | Class | Target outcome | Acceptance signal |
| --- | --- | --- | --- | --- |
| 1 | SCIP-compatible interchange subset | package-ready | Import or export a minimal language-agnostic symbol/reference payload without replacing the native snapshot. | Fixture round-trip proves definitions, references, implementations, and source ranges survive. |
| 2 | Tree-sitter parser packs | optional dependency | Add dependency-scoped parser packs for high-value languages while keeping built-in parsers default. | Missing parsers return typed diagnostics; installed parsers report provenance and version. |
| 3 | Kythe-style anchor and xref model | package-ready | Strengthen stable node identity, anchors, facts, and xref edges for cross-language facts. | Snapshot identity remains deterministic across two runs and preserves source anchors. |
| 4 | CodeQL/Semgrep diagnostics import | package-ready | Import tool findings as observed diagnostics with rule id, source range, severity label, and command provenance. | No PragmaGraph-authored risk judgment appears; imported payload can be exported unchanged. |
| 5 | Test, lint, and build artifact graph | package-ready | Represent test files, failing cases, lint rules, build artifacts, and command outputs as observed graph nodes. | A fixture maps source file -> test/lint artifact -> diagnostic without free-text inference. |
| 6 | Explicit delta refresh manifest | package-ready | Add source hash manifests and changed-path refresh planning without background daemons. | Re-running unchanged roots reports no-op deltas with stable counts and diagnostics. |
| 7 | Store conformance depth | package-ready | Expand JSON/SQLite conformance around query parity, omitted counts, import/export, and failure diagnostics. | Store backends pass one shared suite with snapshot-oracle parity. |
| 8 | Kuzu optional graph store | deferred optional backend | Add graph-native traversal when benchmarks show SQLite is insufficient. | Lazy import, capability report, and traversal benchmarks justify the extra backend. |
| 9 | DuckDB analytics export | deferred optional backend | Export benchmark/report tables for local analytical exploration. | Reports compare snapshots without becoming canonical graph storage. |
| 10 | FTS ranking and explain mode | package-ready | Make lexical search ranking explainable and deterministic across docs, paths, labels, and symbols. | Query results include matched field, rank input, omitted counts, and capability diagnostics. |
| 11 | Vector sidecar reserve | boundary reserve | Prototype vector search over graph node ids without creating graph truth. | Separate boundary acceptance records embedding ownership, deletion, privacy, and export policy. |
| 12 | MCP query server packaging | package-ready or sibling package | Expose search, neighborhood, path, report, and export through MCP tools/resources for non-OpenMinion consumers. | A standalone MCP smoke connects to a snapshot and refuses unsupported or unsafe calls. |
| 13 | GraphFakos UI navigator | package-ready | Improve local visual navigation for search, node detail, path, neighborhood, and omitted diagnostics. | Static artifact lets a user inspect graph shape without OpenMinion. |
| 14 | Snapshot provenance and checksums | package-ready | Add manifest hashes, source-root redaction, parser versions, git posture, and reproducibility metadata. | Two identical roots produce identical manifest hashes with no machine-local path leak. |
| 15 | Privacy and redaction profiles | package-ready | Centralize path, git identity, email, and source-text redaction profiles. | Export tests prove public, local, and private profiles differ only as documented. |
| 16 | Rich document graph | package-ready | Deepen Markdown anchors, headings, backlinks, ADR references, docs-to-code links, and broken-link diagnostics. | A fixture produces doc-section nodes and bidirectional doc/code references. |
| 17 | Git history lineage expansion | package-ready | Extend git overlays to rename chains, churn windows, commit-to-path impact, and symbol lineage where observed. | Tests prove epoch/offset timestamp determinism and privacy-preserving author posture. |
| 18 | Query benchmark matrix | package-ready | Publish small, medium, and fixture-backed benchmark reports for scan, SQLite, graph, and export paths. | Benchmark output is deterministic enough to compare in PRs. |
| 19 | Import/export profiles | package-ready | Define named profiles for native JSON, Graphify-shaped JSON, SCIP subset, DOT, Mermaid, and JSONL. | Each profile declares supported facts, lossy fields, and unsupported diagnostics. |
| 20 | Public recipes and sample datasets | package-ready | Provide one-command examples for codebase indexing, docs indexing, git overlays, store import, UI export, and MCP query. | Public examples run without machine-local paths and are covered by smoke tests. |

## Recommended Order

1. `Rank 10` FTS ranking and explain mode.
2. `Rank 13` GraphFakos UI navigator.
3. `Rank 14` snapshot provenance and checksums.
4. `Rank 1` SCIP-compatible interchange subset.
5. `Rank 16` rich document graph.

This sequence improves product usability first, then broadens interop. It
avoids optional vector, hosted, watcher, and LLM-derived work until the
canonical static-fact product is stronger.

## Non-Goals

1. Do not build a vector sidecar from this spec alone.
2. Do not add hosted services or background watchers from this spec alone.
3. Do not reinterpret commit messages or diagnostics as intent.
4. Do not replace existing storage, service, UI, git, or Graphify specs.
5. Do not open twenty executable lanes at once.

## Promotion Rule

Each roadmap item must be promoted into a narrow tracker before implementation.
That tracker must name:

1. accepted scope,
2. source files and public docs to touch,
3. optional dependency posture,
4. boundary risks,
5. focused validation,
6. package release-check impact,
7. follow-up routing for anything not executed.
