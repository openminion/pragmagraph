# Ten Minute Tour

Status: semantic alpha

This tour shows the shortest standalone path through PragmaGraph: create a
local workspace, open the visual graph, query the materialized store, and export
a certification pack.

## 1. Start The Local Loop

```bash
pragmagraph quickstart . --serve --open --json
```

`quickstart` is the recommended first-run path. It creates
`.pragmagraph/workspace.toml` when needed, refreshes the local snapshot,
materializes the local SQLite store, and opens the first visual investigation
panel through GraphFakos. It does not install watchers, start background
indexers, or call an LLM.

For a self-contained source-checkout example that does not rely on test
fixtures:

```bash
python3.11 examples/quickstart_flow.py
```

## 2. Create A Workspace Config Explicitly

Skip this section if you already ran `quickstart`. These commands show the
same setup in separate steps for scripts and demos.

```bash
pragmagraph workspace-config-init . \
  --out .pragmagraph/workspace.toml \
  --workspace .pragmagraph/workspace \
  --label demo \
  --namespace demo \
  --ui-screen project_health \
  --ui-query RuntimeGraph \
  --json
```

The config file is intentionally small TOML. Relative paths are resolved from
the config file location, which makes checked-in examples and local demos
portable across machines.

Inspect the config and any realized workspace state:

```bash
pragmagraph workspace-config-status .pragmagraph/workspace.toml --json
```

## 3. Open The Visual Graph

```bash
pragmagraph demo-ui \
  --config .pragmagraph/workspace.toml \
  --serve \
  --open \
  --json
```

`demo-ui` initializes the workspace if needed, reuses the config's UI defaults,
and then delegates rendering to the same package-local `pragmagraph.ui`
boundary used by `pragmagraph-ui`.

Write a standalone HTML snapshot instead of serving it:

```bash
pragmagraph demo-ui \
  --config .pragmagraph/workspace.toml \
  --html-out .pragmagraph/pragmagraph-demo.html \
  --artifact-out .pragmagraph/pragmagraph-artifact.json \
  --report-out .pragmagraph/pragmagraph-report.json \
  --json
```

## 4. Search The Workspace Snapshot

```bash
pragmagraph workspace-query \
  --config .pragmagraph/workspace.toml \
  RuntimeGraph \
  --json
```

The lower-level snapshot command accepts the same config when you want to keep
using `query` directly:

```bash
pragmagraph query --config .pragmagraph/workspace.toml RuntimeGraph --json
```

Use the guided investigation bundle when you want a compact “what should I
inspect next?” answer without remembering the snapshot path:

```bash
pragmagraph investigate \
  --config .pragmagraph/workspace.toml \
  RuntimeGraph \
  --preset symbol_map \
  --json
```

Open the same investigation as a visual panel:

```bash
pragmagraph demo-ui \
  --config .pragmagraph/workspace.toml \
  --screen investigation \
  --preset symbol_map \
  --serve \
  --open \
  --json
```

Use the compact repository map for fast orientation:

```bash
pragmagraph repo-map \
  .pragmagraph/workspace/snapshot.json \
  --handoff
```

## 5. Materialize And Explain Store Search

```bash
pragmagraph store-import \
  --config .pragmagraph/workspace.toml \
  --json
```

```bash
pragmagraph store-search-explain \
  --config .pragmagraph/workspace.toml \
  RuntimeGraph \
  --json
```

The explain output reports the materialized search strategy, FTS availability,
candidate node IDs, omitted reasons, and a reproducible `store-query` command.
It does not change ranking or add semantic inference.

## 6. Export A Certification Pack

```bash
pragmagraph certify \
  .pragmagraph/workspace/snapshot.json \
  --markdown-out .pragmagraph/certification.md \
  --json
```

The JSON and Markdown outputs include observed counts, parser coverage, omitted
reasons, privacy posture, topology summary, cross-repository resolution counts
when present, and the canonical snapshot hash.

## 7. Refresh Explicitly

```bash
pragmagraph workspace-refresh --config .pragmagraph/workspace.toml --json
```

PragmaGraph does not install watchers, git hooks, background daemons, or hosted
runtime behavior. Refresh remains explicit and reproducible.

Inspect freshness from the same workspace config:

```bash
pragmagraph freshness --config .pragmagraph/workspace.toml --json
```

## 8. Review A Portable Graph Pack

Export, verify, and review a graph pack before importing it elsewhere:

```bash
pragmagraph graph-pack-export \
  .pragmagraph/workspace/snapshot.json \
  .pragmagraph/graph-pack \
  --include-store \
  --store .pragmagraph/graph.sqlite \
  --json

pragmagraph graph-pack-review \
  .pragmagraph/graph-pack \
  --snapshot-out .pragmagraph/imported-snapshot.json \
  --store-out .pragmagraph/imported.sqlite \
  --json
```

Preview the receive posture visually:

```bash
pragmagraph ui-preview \
  --screen graph_pack_review \
  --graph-pack .pragmagraph/graph-pack \
  --snapshot-out .pragmagraph/imported-snapshot.json \
  --store-out .pragmagraph/imported.sqlite \
  --serve \
  --open \
  --json
```

## 9. Smoke The MCP Surface

Generate config snippets when you want to wire a client manually:

```bash
pragmagraph mcp-config --snapshot .pragmagraph/workspace/snapshot.json --json
pragmagraph mcp-config-smoke --snapshot .pragmagraph/workspace/snapshot.json --json
```

Run a short-lived package-owned MCP smoke when you want protocol proof:

```bash
pragmagraph mcp-smoke --config .pragmagraph/workspace.toml --json
```

The smoke starts `pragmagraph-server` locally, lists MCP tools, calls
`pragmagraph_investigate`, and exits. It does not launch Claude, Cursor, or any
other user client.
