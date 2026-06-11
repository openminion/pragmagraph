# PragmaGraph Graphify Interop

Status: semantic alpha

## Purpose

Graphify interop gives external tools a deterministic JSON bridge between a
PragmaGraph snapshot and a Graphify-shaped graph payload.

The package-owned helpers are:

- `to_graphify_payload(snapshot)`
- `snapshot_from_graphify_payload(payload)`
- `GRAPHIFY_INTEROP_FORMAT`

## CLI

```bash
pragmagraph graphify-export .pragmagraph/snapshot.json > graphify.json
pragmagraph graphify-import graphify.json --out .pragmagraph/imported.json
```

## Payload Shape

The exported payload is a JSON object with:

- `format`: the PragmaGraph Graphify interop format string,
- `interop_schema_version`: explicit PragmaGraph interop schema version,
- `source`: source snapshot metadata,
- `nodes`: sorted node rows with `id`, `type`, `label`, and `properties`,
- `edges`: sorted edge rows with `id`, `type`, `source`, `target`, and
  `properties`,
- `omitted`: PragmaGraph omitted diagnostics,
- `stats`: snapshot stats.

The supported import subset reads `nodes` and `edges` with Graphify-style
`type`, `source`, `target`, `label`, and `properties` fields. Unknown payload
keys are ignored. Consumers should preserve `interop_schema_version` and may
use it to guard fixture drift.

## Boundary

This is not a Graphify runtime client and does not import Graphify. It does not
promise parity with hosted Graphify APIs, graph database storage, visualization,
or Graphify-specific query execution.

The goal is a stable, deterministic interchange shape so OpenMinion and other
agent runtimes can test provider swapability without binding themselves to one
graph backend.
