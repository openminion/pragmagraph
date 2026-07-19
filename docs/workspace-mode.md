# Workspace Mode

Status: semantic alpha
Scope: package-local persistent local workspace contract

PragmaGraph ships a package-owned persistent local workspace surface for
repeatable local operation without widening into background automation.

## Public root

- `pragmagraph.workspace`

## What it provides

- deterministic workspace metadata via `WorkspaceMetadata` and `WorkspacePaths`
- one-command workspace creation via `initialize_workspace(...)`
- repeatable workspace refresh via `refresh_workspace(...)`
- typed workspace status inspection via `load_workspace_status(...)`
- public TOML workspace config via `WorkspaceConfig`,
  `save_workspace_config(...)`, and `load_workspace_config(...)`
- workspace-backed service startup via `LocalQueryService.from_workspace(...)`
  and `pragmagraph serve --workspace ...`
- deterministic multi-root overlays via `WorkspaceRoot` and
  `index_multi_root(...)`

## CLI entrypoints

- `pragmagraph workspace-init <root> --workspace <dir> --json`
- `pragmagraph workspace-refresh <dir> --json`
- `pragmagraph workspace-refresh --config .pragmagraph/workspace.toml --json`
- `pragmagraph workspace-status <dir> --json`
- `pragmagraph workspace-status --config .pragmagraph/workspace.toml --json`
- `pragmagraph workspace-query --config .pragmagraph/workspace.toml RuntimeGraph --json`
- `pragmagraph workspace-config-init <root> --out .pragmagraph/workspace.toml --json`
- `pragmagraph workspace-config-status .pragmagraph/workspace.toml --json`
- `pragmagraph demo-ui --config .pragmagraph/workspace.toml --serve --open`
- `pragmagraph serve --workspace <dir>`
- `pragmagraph multi-root-index --root api=../api --root web=../web --out snapshot.json --json`

## Workspace config

The config file is a small package-owned TOML contract for first-run and
repeatable demos:

```toml
schema_version = "pragmagraph.workspace_config.v1alpha1"
label = "demo"
namespace = "demo"
root_path = "."
workspace_path = ".pragmagraph/workspace"
git_identity_mode = "name_email_hash"
store_path = "graph.sqlite"

[ui]
screen = "project_health"
query = "RuntimeGraph"
```

Relative paths are resolved from the config file directory. The config records
local execution defaults only; it does not create a background operator or
hosted runtime.

The current screen values are `search`, `result_detail`, `neighborhood`,
`path`, `provider_status`, and `project_health`. `project_health` uses the
existing provider-status renderer while exposing PragmaGraph-owned structural
health facts in the provider payload. When launched from a workspace config, it
also includes last-refresh counts and store availability if a materialized store
has been imported.

## Workspace layout

Each workspace directory owns one deterministic file set:

- `workspace.json`
- `profile.json`
- `snapshot.json`
- `manifest.json`
- `status.json`
- `cache/extraction-cache.json`

Workspace refresh is the one mode that enables the package-owned extraction
cache without a caller-supplied path. The cache is rebuildable and
non-canonical; `snapshot.json` remains the portable truth. Status output
reports whether the cache is present, and refresh output reports parsed versus
reused paths.

## Boundary

Workspace mode stays inside the current PragmaGraph contract:

1. local-first
2. single-process
3. explicitly refreshed
4. structurally grounded

It does **not** reopen:

1. file watchers
2. scheduled refresh
3. git-hook-triggered refresh
4. hosted auth or remote multi-tenant operation
5. semantic interpretation of refresh outcomes

Multi-root composition is an explicit one-shot index operation. Each root must
have a unique name/namespace, every fact retains root attribution, and argument
order does not affect output. It does not add multi-root watching or background
refresh.
