# PragmaGraph Changelog

Status: active
Last updated: 2026-06-20

This file tracks package-facing release notes for `pragmagraph`.

## Unreleased

### Added

- Added opt-in changed-only extraction caches, refresh work diagnostics, and
  git-backed identity transitions.
- Added explicit SQLite v1-to-v2 migration, atomic normalized-row delta apply,
  indexed lexical query strategies, and store-native filtered traversal.
- Added deterministic generated scale evidence for 1,000- and 10,000-node CI
  profiles, with a 100,000-node release profile.
- Added deterministic query cursors and work budgets, multi-root overlays, CI
  snapshot deltas, artifact-specific facts, and exact manifest/lock resolution.
- Added a loss-aware SCIP JSON subset, caller-fed compiler/LSP fact bridge,
  export redaction profiles, and read-only MCP resources.
- Added package-local public contributor references for testing, engineering
  patterns, agent bootstrap, and code-quality enforcement.

### Changed

- Polished the public package docs surface so external contributors can follow
  package-local references without internal workspace context.
- Advanced the indexer contract to `pragmagraph.indexer.v1alpha2` so existing
  extraction caches invalidate before artifact-specific facts are materialized.

### Notes

- The project remains in semantic alpha. Until the next tagged release,
  changes may land ahead of a published semantic-versioned changelog entry.
