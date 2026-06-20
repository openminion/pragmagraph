# PragmaGraph Engineering Patterns

Status: active
Last updated: 2026-06-20

Purpose: give public contributors one package-local summary of the engineering
patterns that shape `pragmagraph` changes.

## Core rule

Prefer typed, deterministic, reproducible observed-fact contracts over
implicit behavior or host-specific shortcuts.

## Main package split

Use this source-tree ladder when deciding where code belongs:

1. `models/` and `contracts/` own snapshots, DTOs, and typed records.
2. `query/` owns local query and traversal request/result surfaces.
3. `storage/` owns persistence and snapshot storage helpers.
4. `report/`, `export/`, and `graphify/` own their named package boundaries.
5. `refresh/`, `service/`, `workspace/`, `operations.py`, and `ui/` own their
   explicit standalone surfaces.

## Shared-owner rules

1. Shared constants should live in their canonical owner rather than being
   repeated inline.
2. Public roots should stay intentional; not every internal import path is a
   stable promise.
3. Keep compatibility helpers thin and explicit.

## Runtime-boundary rules

1. Keep outputs deterministic and typed.
2. PragmaGraph owns observed, reproducible facts; do not add LLM-owned,
   judgmental, or lossy semantic behavior to the package core.
3. Keep parser, refresh, and service contracts explicit.
4. Keep host-framework behavior outside the package unless the public contract
   explicitly owns it.

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
