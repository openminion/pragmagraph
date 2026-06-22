# PragmaGraph Package Docs

Status: semantic alpha

This directory holds the public package documentation for standalone
`pragmagraph`.

## Package-local references

- [`getting-started.md`](getting-started.md) gives the
  package-local bootstrap and execution summary for contributors and automation.
- [`engineering-patterns.md`](engineering-patterns.md)
  summarizes the package-local engineering and boundary rules for contributors.
- [`code-quality-enforcement.md`](code-quality-enforcement.md)
  summarizes the active public quality gates and validation posture.
- [`testing-and-validation.md`](testing-and-validation.md)
  records the package-local install, smoke, test, lint, and release-check
  flow.
- [`report-mode.md`](report-mode.md) records the structural
  report contract and CLI shape.
- [`export-mode.md`](export-mode.md) records DOT/Mermaid
  text export contracts and CLI shape.
- [`service-mode.md`](service-mode.md) records the local
  service request/response contract.
- [`workspace-mode.md`](workspace-mode.md) records the
  package-owned persistent local workspace contract.
- [`refresh-operations.md`](refresh-operations.md) records
  the package-owned explicit refresh/profile/status surface.
- [`ui-contracts.md`](ui-contracts.md) records the
  package-owned `pragmagraph.ui` boundary for the future OpenMinion workbench
  surface.
- [`benchmarking.md`](benchmarking.md) records the
  package-owned benchmark surface and repo-local regression fixture policy.
- [`graphify-interop.md`](graphify-interop.md) records the
  deterministic Graphify-shaped JSON import/export contract.
- [`git-history-mode.md`](git-history-mode.md) records the
  local git-overlay contract, privacy posture, and CLI shape.
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

The `0.0.1` semantic alpha defines the current public package contract:
immutable DTOs, JSON snapshots, local indexing, deterministic
query/traversal/report/export helpers, Graphify-shaped interop, package-local
service and UI boundary contracts, explicit refresh/profile/status helpers,
workspace persistence helpers, git-aware provenance overlays, benchmark
helpers, and package-owned validation fixtures.

## Boundary shorthand

1. PragmaGraph is the third brain for static, observed, reproducible facts from
   code, docs, artifacts, and history.
2. Sophiagraph is the second brain for agent-owned memory: learned preferences,
   operator pins, summaries, decisions, and judgments.
3. Sophia may cite Pragma; Pragma never stores Sophia's judgments.
