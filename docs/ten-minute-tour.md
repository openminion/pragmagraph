# Ten Minute Tour

Status: semantic alpha

This tour shows the shortest standalone path through PragmaGraph: index a local
project, open the visual graph, query the materialized store, and export a
certification pack.

## 1. Create A Workspace Config

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

## 2. Open The Visual Graph

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

## 3. Search The Workspace Snapshot

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

Use the compact repository map for fast orientation:

```bash
pragmagraph repo-map \
  .pragmagraph/workspace/snapshot.json \
  --handoff
```

## 4. Materialize And Explain Store Search

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

## 5. Export A Certification Pack

```bash
pragmagraph certify \
  .pragmagraph/workspace/snapshot.json \
  --markdown-out .pragmagraph/certification.md \
  --json
```

The JSON and Markdown outputs include observed counts, parser coverage, omitted
reasons, privacy posture, topology summary, cross-repository resolution counts
when present, and the canonical snapshot hash.

## 6. Refresh Explicitly

```bash
pragmagraph workspace-refresh --config .pragmagraph/workspace.toml --json
```

PragmaGraph does not install watchers, git hooks, background daemons, or hosted
runtime behavior. Refresh remains explicit and reproducible.
