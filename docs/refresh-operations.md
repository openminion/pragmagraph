# Refresh Operations

Status: semantic alpha
Scope: package-local refresh planning, profiles, and status surface

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
- opt-in changed-only extraction through a deterministic local cache bundle
- root-backed service refresh-state reporting through
  `LocalQueryService.current_refresh_status()`, `LocalQueryService.status()`,
  and the `status` service method

## CLI entrypoints

- `pragmagraph refresh-plan <root> --manifest-in <manifest.json> --json`
- `pragmagraph profile-init <root> --out <profile.json> --snapshot-out <snapshot.json> --manifest-out <manifest.json> --state-out <status.json> --json`
- `pragmagraph profile-run <profile.json> --json`
- `pragmagraph refresh-status <status.json> --json`

Direct refresh keeps full mode as the default. To opt in, name cache input and
output explicitly:

```bash
pragmagraph refresh . \
  --out .pragmagraph/snapshot.json \
  --manifest-out .pragmagraph/manifest.json \
  --cache-in .pragmagraph/extraction-cache.json \
  --cache-out .pragmagraph/extraction-cache.json \
  --json
```

Workspace mode owns `cache/extraction-cache.json` under the workspace root.
It never writes cache state into the indexed source root. A corrupt or
incompatible cache triggers a full extraction rebuild, reports a typed
`cache_fallback_reason`, and is replaced only after snapshot, manifest, and
status persistence succeeds.

Refresh results expose `work` counts for walked and parsed paths, source bytes
hashed, fragment reuse, resolution/git overlay rebuilds, and cache fallback.
Git-proven, unambiguous renames may also appear as non-canonical
`identity_transitions`; canonical snapshots continue to use current paths.

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
- added / removed node, edge, and omitted-diagnostic counts from the structural
  snapshot delta
- omitted diagnostic reason counts from the latest snapshot
- snapshot identity
- typed error code/message for the last failed attempt

Those facts are meant to be inspectable by local callers and host runtimes
without forcing them to rebuild refresh bookkeeping around raw snapshot files.

## Service readiness

Long-lived local services expose refresh posture through the `status` method and
the `pragma://status` MCP resource. This is a read-only view over the loaded
state. It does not start a refresh, watch the source tree, schedule work, or
interpret the meaning of changes.

The readiness payload reports whether explicit refresh is currently available,
why it is or is not available, and whether the expected local artifacts are
present. Snapshot-backed and store-backed services report unsupported refresh
with typed reasons; root-backed and workspace-backed services report that an
explicit refresh can be requested by the caller.
