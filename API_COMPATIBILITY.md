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
- `pragmagraph.portability`

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
6. release/install smoke for built artifacts.

## Non-goals

This policy does not promise:

1. host-framework orchestration semantics,
2. graph-database storage behavior,
3. Graphify artifact mapping,
6. semantic inference of facts, labels, relations, or summaries from prose,
7. compatibility for undocumented import paths.
