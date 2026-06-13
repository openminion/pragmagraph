# Refresh Operations

PragmaGraph ships a package-owned explicit refresh operations layer for
repeatable local ingest/update workflows without widening into watchers,
schedulers, git hooks, or background daemons.

## Public root

- `pragmagraph.operations`

## What it provides

- deterministic refresh previews via `build_refresh_plan(...)`
- saved invocation profiles via `RefreshProfile`,
  `build_refresh_profile(...)`, `save_refresh_profile(...)`, and
  `load_refresh_profile(...)`
- persistent refresh state ledgers via `RefreshStatus`,
  `save_refresh_status(...)`, and `load_refresh_status(...)`
- one-command explicit runs via `run_refresh_profile(...)`
- root-backed service refresh-state reporting through
  `LocalQueryService.current_refresh_status()` and `health`

## CLI entrypoints

- `pragmagraph refresh-plan <root> --manifest-in <manifest.json> --json`
- `pragmagraph profile-init <root> --out <profile.json> --snapshot-out <snapshot.json> --manifest-out <manifest.json> --state-out <status.json> --json`
- `pragmagraph profile-run <profile.json> --json`
- `pragmagraph refresh-status <status.json> --json`

## Boundary

This surface stays inside the current PragmaGraph contract:

1. local-first
2. single-process
3. explicitly invoked
4. structurally grounded

It does **not** reopen:

1. file watchers
2. scheduled refresh
3. git-hook-triggered refresh
4. hosted auth or multi-tenant orchestration
5. semantic interpretation of refresh outcomes

## Typed status facts

The persisted refresh ledger intentionally records observed operational facts
only:

- root path
- namespace
- status
- last attempt / success / failure timestamps
- snapshot and manifest paths
- parser set
- changed / unchanged / removed path counts
- snapshot identity
- typed error code/message for the last failed attempt

Those facts are meant to be inspectable by local callers and host runtimes
without forcing them to rebuild refresh bookkeeping around raw snapshot files.
