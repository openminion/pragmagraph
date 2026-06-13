# Workspace Mode

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

## CLI entrypoints

- `pragmagraph workspace-init <root> --workspace <dir> --json`
- `pragmagraph workspace-refresh <dir> --json`
- `pragmagraph workspace-status <dir> --json`
- `pragmagraph serve --workspace <dir>`

## Workspace layout

Each workspace directory owns one deterministic file set:

- `workspace.json`
- `profile.json`
- `snapshot.json`
- `manifest.json`
- `status.json`

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
