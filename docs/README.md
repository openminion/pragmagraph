# PragmaGraph Package Docs

This package-local docs directory is reserved for package-owned documentation.

Current canonical planning docs live in the host repository:

- `docs/reference/second-vs-third-brain-quick-reference.md`
- `docs/discussions/sophiagraph-pragmagraph-boundary-2026-05-27.md`
- `docs/discussions/pragmagraph-third-brain-market-research-2026-05-31.md`
- `docs/specs/pragmagraph-mvp-openminion-usability-spec.md`
- `docs/trackers/qa/pragmagraph-mvp-openminion-usability-tracker.md`
- `docs/discussions/pragmagraph-graphify-gap-research-2026-05-31.md`
- `docs/specs/pragmagraph-graphify-parity-expansion-spec.md`
- `docs/trackers/archive/2026/pragmagraph-graphify-parity-expansion-tracker.md`
- `docs/specs/openminion-third-brain-provider-abstraction-readiness-spec.md`
- `docs/trackers/qa/openminion-third-brain-provider-abstraction-readiness-tracker.md`
- `docs/specs/openminion-pragmagraph-provider-adapter-swapability-spec.md`
- `docs/trackers/archive/2026/openminion-pragmagraph-provider-adapter-swapability-tracker.md`
- `docs/specs/pragmagraph-package-baseline-spec.md`
- `docs/trackers/archive/2026/pragmagraph-package-baseline-tracker.md`

Package-local reusable docs:

- `docs/public-package-readme-template.md` records the public README header,
  trust, and brand-use format used by PragmaGraph and sibling standalone
  packages.
- `docs/report-mode.md` records the structural report contract and CLI shape.
- `docs/export-mode.md` records DOT/Mermaid text export contracts and CLI shape.
- `docs/graphify-interop.md` records the deterministic Graphify-shaped JSON
  import/export contract.
- `docs/certification-readiness-matrix.md` records the current standalone and
  OpenMinion proof targets for the public package surface.

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
   query APIs, CLI, tests, and OpenMinion handoff fixtures.
2. OpenMinion abstraction tracker owns provider registration, conformance,
   context assembly, telemetry, graceful fallback, and provider swapability.
