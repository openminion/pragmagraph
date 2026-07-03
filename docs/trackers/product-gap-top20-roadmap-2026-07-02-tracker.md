# PragmaGraph Product Gap Top 20 Roadmap Tracker

Date: 2026-07-02
Status: draft discussion, not executable
Owner: PragmaGraph
Related:
[`../specs/product-gap-top20-roadmap-2026-07-02-spec.md`](../specs/product-gap-top20-roadmap-2026-07-02-spec.md),
[`../storage-interchange.md`](../storage-interchange.md),
[`../advanced-structural-views.md`](../advanced-structural-views.md),
[`../service-mode.md`](../service-mode.md),
[`../ui-contracts.md`](../ui-contracts.md),
[`../git-history-mode.md`](../git-history-mode.md)

## Purpose

Track discussion of the next twenty PragmaGraph product gaps. This tracker is
a candidate register only. It does not authorize implementation.

## Execution Gate

Do not start code from this tracker. Promote exactly one bounded item into a
new executable tracker when it is ready for implementation.

Promotion must preserve these rules:

1. static observed facts stay canonical,
2. optional dependencies stay optional and capability-reported,
3. vector/LLM/hosted/background behavior needs a separate scope decision,
4. public examples must use repo-relative paths,
5. no version bump happens unless explicitly requested.

## Candidate Board

| ID | Priority | Class | Status | Candidate | Promotion target |
| --- | --- | --- | --- | --- | --- |
| `PGT20-01` | P0 | interchange | `todo` | SCIP-compatible interchange subset. | New package tracker for minimal SCIP import/export profile. |
| `PGT20-02` | P0 | parser | `todo` | Optional Tree-sitter parser packs. | New parser-pack tracker with missing-dependency diagnostics. |
| `PGT20-03` | P0 | xref | `todo` | Kythe-style anchor and cross-reference model. | New xref identity tracker. |
| `PGT20-04` | P1 | diagnostics | `todo` | CodeQL and Semgrep diagnostics import. | New observed-diagnostics import tracker. |
| `PGT20-05` | P1 | artifact graph | `todo` | Test, lint, and build artifact graph. | New artifact ingestion tracker. |
| `PGT20-06` | P0 | refresh | `todo` | Explicit delta refresh manifest. | New explicit-refresh manifest tracker. |
| `PGT20-07` | P0 | storage | `todo` | Store conformance depth. | New storage conformance tracker. |
| `PGT20-08` | P2 | optional backend | `todo` | Kuzu optional graph store. | Deferred until traversal benchmarks show need. |
| `PGT20-09` | P2 | optional backend | `todo` | DuckDB analytics export. | Deferred until report workloads prove value. |
| `PGT20-10` | P0 | search | `todo` | FTS ranking and explain mode. | Recommended first executable tracker. |
| `PGT20-11` | P2 | boundary reserve | `todo` | Vector sidecar reserve. | Boundary-amendment tracker before implementation. |
| `PGT20-12` | P1 | MCP | `todo` | MCP query server packaging. | Package or sibling-server tracker after scope review. |
| `PGT20-13` | P0 | UI | `todo` | GraphFakos UI navigator. | Recommended early executable tracker. |
| `PGT20-14` | P0 | provenance | `todo` | Snapshot provenance and checksums. | Recommended early executable tracker. |
| `PGT20-15` | P1 | privacy | `todo` | Privacy and redaction profiles. | New export/privacy tracker. |
| `PGT20-16` | P0 | docs graph | `todo` | Rich document graph. | Recommended early executable tracker. |
| `PGT20-17` | P1 | git | `todo` | Git history lineage expansion. | New git-overlay follow-up tracker. |
| `PGT20-18` | P1 | benchmark | `todo` | Query benchmark matrix. | New benchmark tracker. |
| `PGT20-19` | P1 | export | `todo` | Import/export profiles. | New profile matrix tracker. |
| `PGT20-20` | P1 | examples | `todo` | Public recipes and sample datasets. | New examples and smoke tracker. |

## Suggested First Promotion

Promote `PGT20-10` first.

Reason:

1. it improves the existing SQLite/JSON store surface,
2. it helps both CLI and UI users immediately,
3. it has no optional dependency or boundary expansion,
4. it makes later MCP and UI work easier to verify.

## Boundary Reserves

Rows that must not be implemented directly from this tracker:

1. `PGT20-08` Kuzu backend,
2. `PGT20-09` DuckDB backend,
3. `PGT20-11` vector sidecar,
4. hosted service variants of `PGT20-12`,
5. background refresh variants of `PGT20-06`.

## Validation Expectations For Promoted Rows

Every promoted row should include:

1. focused pytest coverage,
2. targeted Ruff over touched source/tests/examples,
3. `PYTHONDONTWRITEBYTECODE=1 make check`,
4. `PYTHONDONTWRITEBYTECODE=1 make release-check` when public imports,
   packaging, examples, UI artifacts, or release surfaces change,
5. docs updates for any public CLI/API behavior.

## Change Log

| Date | Change |
| --- | --- |
| 2026-07-02 | Created review-only top-20 gap register from current package state and public product/open-source research. |
