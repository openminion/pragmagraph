# PragmaGraph Package Docs

This package-local docs directory is reserved for standalone `pragmagraph`
documentation and public release references.

Package-local reference docs:

- `docs/reference/report-mode.md` records the structural report contract and
  CLI shape.
- `docs/reference/export-mode.md` records DOT/Mermaid text export contracts and
  CLI shape.
- `docs/reference/service-mode.md` records the local service request/response
  contract.
- `docs/reference/ui-contracts.md` records the package-owned `pragmagraph.ui`
  boundary for the future OpenMinion workbench surface.
- `docs/reference/benchmarking.md` records the package-owned benchmark surface
  and repo-local regression fixture policy.
- `docs/reference/graphify-interop.md` records the deterministic
  Graphify-shaped JSON import/export contract.
- `docs/reference/certification-readiness-matrix.md` records the current
  standalone and OpenMinion proof targets for the public package surface.

Package-local code/docs boundaries:

1. `README.md` is the public package contract and install surface.
2. `API_COMPATIBILITY.md` records the supported public import roots and
   top-level export policy.
3. `RELEASING.md` records the package-local release and PyPI publish flow.
4. `scripts/release_check.py` is the canonical package release smoke entrypoint.

Repository-local but not package API:

1. `tests/fixtures/repos/` holds regression fixtures used by benchmarks,
   examples, and deterministic package tests.
2. `tests/contracts/` holds OpenMinion-facing contract snapshots used by
   adapter and provider-swap validation.
3. Host-framework planning, tracker, and swapability docs remain in the
   workspace-root `docs/` tree rather than this package-local docs directory.

Current canonical planning docs live in the host repository:

- `docs/reference/second-vs-third-brain-quick-reference.md`
- `docs/discussions/sophiagraph-pragmagraph-boundary-2026-05-27.md`
- `docs/discussions/pragmagraph-third-brain-market-research-2026-05-31.md`
- `docs/specs/pragmagraph-mvp-openminion-usability-spec.md`
- `docs/trackers/qa/pragmagraph-mvp-openminion-usability-tracker.md`
- `docs/discussions/pragmagraph-graphify-gap-research-2026-05-31.md`
- `docs/specs/pragmagraph-graphify-parity-expansion-spec.md`
- `docs/trackers/qa/pragmagraph-graphify-parity-expansion-tracker.md`
- `docs/specs/pragmagraph-local-query-service-spec.md`
- `docs/trackers/qa/pragmagraph-local-query-service-tracker.md`
- `docs/specs/openminion-third-brain-provider-abstraction-readiness-spec.md`
- `docs/trackers/qa/openminion-third-brain-provider-abstraction-readiness-tracker.md`
- `docs/specs/openminion-pragmagraph-provider-adapter-swapability-spec.md`
- `docs/trackers/qa/openminion-pragmagraph-provider-adapter-swapability-tracker.md`
- `docs/specs/pragmagraph-package-baseline-spec.md`
- `docs/trackers/qa/pragmagraph-package-baseline-tracker.md`

The `0.0.1` semantic alpha defines the first narrow graph-facing contracts:
immutable DTOs, JSON snapshots, local indexing, deterministic query/traversal,
CLI commands, and OpenMinion handoff fixtures.

Boundary shorthand:

1. PragmaGraph is the third brain for static, observed, reproducible facts from
   code, docs, artifacts, and history.
2. Sophiagraph is the second brain for agent-owned memory: learned preferences,
   operator pins, summaries, decisions, and judgments.
3. Sophia may cite Pragma; Pragma never stores Sophia's judgments.

Tracker split:

1. PragmaGraph package tracker owns package contracts, snapshots, indexing,
   query APIs, CLI, tests, and OpenMinion contract snapshots.
2. OpenMinion abstraction tracker owns provider registration, conformance,
   context assembly, telemetry, graceful fallback, and provider swapability.
