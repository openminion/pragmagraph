# PragmaGraph Engineering Patterns

Status: active
Last updated: 2026-11-01

Purpose: give public contributors one package-local summary of the engineering
patterns that shape `pragmagraph` changes.

## Core rule

Prefer typed, deterministic, reproducible observed-fact contracts over
implicit behavior or host-specific shortcuts.

## Main package split

Use this source-tree ladder when deciding where code belongs:

1. `contracts/` and `models/` own schema versions, typed errors, immutable
   snapshots, and observed-fact DTOs.
2. `adapters/`, `parsers/`, and `interchange/` own deterministic source intake,
   parser registration, and external structural fact bridges.
3. `query/`, `investigate/`, and `navigation/` own deterministic lookup,
   traversal, explanation, and guided inspection over existing snapshots.
4. `storage/`, `refresh/`, and `operations.py` own snapshot persistence,
   canonical deltas, repeatable ingest plans, and operation ledgers.
5. `workspace/` owns persistent single- and multi-root workspace contracts and
   exact cross-root composition.
6. `service/` owns repeated local query behavior; `server/` owns bounded MCP
   transport, tools, resources, and consumer smoke.
7. `viewer/` owns provider-neutral envelope and scale contracts. `ui/` owns the
   PragmaGraph adapter and package preview wiring; shared viewer behavior stays
   in GraphFakos.
8. `report/`, `export/`, `graphify/`, `topology/`, `docgraph/`, `planner/`,
   `certification/`, and `lineage/` own their named structural views.

## Shared-owner rules

1. Shared constants should live in their canonical owner rather than being
   repeated inline.
2. Public roots should stay intentional; not every internal import path is a
   stable promise.
3. Keep compatibility helpers thin and explicit.
4. Keep `__main__.py` as orchestration; domain command registration belongs
   with the owning CLI module.

## Runtime-boundary rules

1. Keep outputs deterministic and typed.
2. PragmaGraph owns observed, reproducible facts; do not add LLM-owned,
   judgmental, or lossy semantic behavior to the package core.
3. Keep parser, refresh, and service contracts explicit.
4. Keep host-framework behavior outside the package unless the public contract
   explicitly owns it.

## Observed-fact discipline

1. Indexers and parsers record reproducible source evidence. They do not invent
   semantic intent, quality judgments, or relationships unsupported by the
   input.
2. Preserve source identity, parser/version facts, content hashes, provenance,
   freshness, and omission counts through snapshots, reports, viewer envelopes,
   and interchange formats.
3. Optional SCIP, compiler, LSP, Git, and artifact facts stay caller-fed and
   attributable. Their absence is unavailable evidence, not proof that a
   relationship does not exist.
4. Redaction and export profiles may omit data, but must report the applied
   profile and resulting omissions rather than silently changing graph truth.

## Workspace and operation rules

1. Workspace configuration resolves roots and canonical snapshots explicitly;
   do not infer a different workspace from the current process directory after
   initialization.
2. Refresh and ingest operations use stable invocation facts, content hashes,
   and status ledgers so reruns are explainable and do not create ambiguous
   duplicate state.
3. Queries, investigation bundles, UI previews, and MCP resources are read-only
   over observed snapshots unless an owner explicitly documents a mutation.
4. Keep HTTP/MCP/CLI envelopes transport-owned while preserving the same typed
   package error facts.

## Viewer integration

PragmaGraph adapts observed snapshots into GraphFakos contracts. Keep adapter
logic in `ui/`; do not copy GraphFakos rendering, routes, browser assets, or
viewer assertions. Large envelopes must distinguish raw, rendered, clustered,
and omitted counts so scale claims remain honest.

## Cleanup and refactor rules

1. Preserve ownership clarity over broad rewrites.
2. Keep boundary changes paired with matching tests and docs.
3. Keep public docs portable and package-local.

## Use with

Read this doc together with:

1. [`code-quality-enforcement.md`](code-quality-enforcement.md)
2. [`getting-started.md`](getting-started.md)
3. [`testing-and-validation.md`](testing-and-validation.md)
4. [`source-tree-owner-map.md`](source-tree-owner-map.md)

Apply the [comment and docstring review](../CODE_QUALITY.md#comment-and-docstring-review)
to the final diff, including tests and scripts.
