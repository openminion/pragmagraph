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
- workspace-backed service startup via `LocalQueryService.from_workspace(...)`
  and `pragmagraph serve --workspace ...`
- deterministic multi-root overlays via `WorkspaceRoot` and
  `index_multi_root(...)`

## CLI entrypoints

- `pragmagraph workspace-init <root> --workspace <dir> --json`
- `pragmagraph workspace-refresh <dir> --json`
- `pragmagraph workspace-status <dir> --json`
- `pragmagraph serve --workspace <dir>`
- `pragmagraph multi-root-index --root api=../api --root web=../web --out snapshot.json --json`

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
