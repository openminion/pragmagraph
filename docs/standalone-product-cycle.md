# Standalone Product Cycle

Status: semantic alpha

This page shows the public standalone loop for using PragmaGraph without
OpenMinion: index observed facts, navigate them locally, review refresh
changes, move them between machines, and expose them to MCP clients.

## One local workbench command

Use `workbench` when you want the quickest local UI over a real project:

```bash
pragmagraph workbench \
  --root . \
  --workspace .pragmagraph/workspace \
  --screen evidence \
  --serve \
  --open \
  --json
```

The command initializes an explicit local workspace when needed, writes a
canonical snapshot, materializes a local SQLite store, and renders the
GraphFakos-backed local visual shell. It does not start a background watcher,
schedule refresh, or call a hosted service. JSON output includes
`next_commands` with copyable query, investigation, freshness, report,
backend-probe, graph-pack, MCP-config, MCP-smoke, and store-health commands for
the files that were just created.

## Guided investigation

Use `investigate` when you want the smallest useful answer to "what should I
inspect next?" for one static graph question:

```bash
pragmagraph investigate \
  .pragmagraph/snapshot.json \
  RuntimeGraph \
  --preset symbol_map \
  --json
```

The payload contains matched nodes, structural match reasons, direct
neighborhood facts for the first match, a path when two matches are present,
freshness facts, and copyable next commands. Presets are `search`, `file_map`,
`symbol_map`, `doc_links`, `changed_recently`, `orphans`, and `high_degree`.
They filter observed facts only; they do not infer intent, risk, priority, or
architectural meaning.

For static HTML output instead of serving:

```bash
pragmagraph workbench \
  --root . \
  --workspace .pragmagraph/workspace \
  --screen search \
  --html-out .pragmagraph/workbench.html \
  --artifact-out .pragmagraph/workbench-artifact.json \
  --json
```

## Refresh and delta review

PragmaGraph refresh is explicit. Run refresh when you want to update observed
facts:

```bash
pragmagraph workspace-refresh .pragmagraph/workspace --json
```

Open the delta review screen from workspace refresh status:

```bash
pragmagraph workbench \
  --workspace .pragmagraph/workspace \
  --screen delta_review \
  --serve \
  --open \
  --json
```

Or compare two canonical snapshots directly:

```bash
pragmagraph ui-preview \
  --screen delta_review \
  --snapshot .pragmagraph/after.json \
  --before-snapshot .pragmagraph/before.json \
  --after-snapshot .pragmagraph/after.json \
  --artifact-out .pragmagraph/delta-artifact.json \
  --json
```

The delta review payload reports structural additions, removals, changed fact
IDs, and refresh ledger counts. It does not infer risk, intent, priority, or
meaning.

## Graph packs

Use a graph pack when you want one portable directory containing the canonical
snapshot and optional rebuildable store:

```bash
pragmagraph graph-pack-export \
  .pragmagraph/snapshot.json \
  .pragmagraph/graph-pack \
  --include-store \
  --json

pragmagraph graph-pack-inspect .pragmagraph/graph-pack --json
pragmagraph graph-pack-verify .pragmagraph/graph-pack --json

pragmagraph graph-pack-import \
  .pragmagraph/graph-pack \
  --snapshot-out .pragmagraph/imported-snapshot.json \
  --store-out .pragmagraph/imported.sqlite \
  --json
```

The pack is a handoff bundle, not a new canonical format. The canonical fact
artifact remains `snapshot.json`; materialized stores remain rebuildable.
`graph-pack-verify` checks the manifest, snapshot counts, file checksums,
optional store export parity, and optional evidence JSON before a receiver
imports the pack.

Review the receive posture before importing:

```bash
pragmagraph graph-pack-review \
  .pragmagraph/graph-pack \
  --snapshot-out .pragmagraph/imported-snapshot.json \
  --store-out .pragmagraph/imported.sqlite \
  --json
```

`graph-pack-review` is read-only. It reports whether the pack is ready to
import and emits copyable import commands only for caller-selected output paths.

## Storage and search backends

List current and reserved backend capabilities:

```bash
pragmagraph store-backends --json
pragmagraph store-backends --probe-optional --json
```

Inspect one concrete backend path:

```bash
pragmagraph store-backends \
  --backend sqlite \
  --path .pragmagraph/graph.sqlite \
  --json
```

Current available backends are the canonical JSON snapshot store and the local
SQLite materialized store. Kuzu, DuckDB, remote stores, and vector sidecars are
reserved or boundary-gated until a future release accepts their scope. Optional
backend probing reports whether a reserved Python package is installed without
making that backend active or canonical.

## MCP client setup

Generate portable stdio snippets for MCP-capable clients:

```bash
pragmagraph mcp-config \
  --snapshot .pragmagraph/snapshot.json \
  --json

pragmagraph mcp-config-smoke \
  --snapshot .pragmagraph/snapshot.json \
  --json
```

The generated snippets point clients at `pragmagraph-server serve-stdio`. The
server exposes deterministic structural tools and read-only `pragma://...`
resources over one loaded snapshot or explicit root. It does not expose
summarization, intent inference, or memory-writing tools. The JSON payload also
lists supported clients and setup next steps so a receiver can paste the right
stdio config without reading server internals.
`mcp-config-smoke` validates the generated stdio command and client snippets
without starting a client or probing a user machine.
