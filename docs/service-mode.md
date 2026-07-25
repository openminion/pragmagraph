# Service Mode

Status: semantic alpha
Scope: local single-process query service contract

PragmaGraph now ships a package-owned local service surface for repeated graph
queries without reloading state on every call.

## Public root

- `pragmagraph.service`

## CLI entrypoints

- `pragmagraph serve --snapshot <snapshot.json>`
- `pragmagraph serve --root <repo-root> --namespace <name>`
- `pragmagraph serve --root <repo-root> --cache <cache.json>`
- `pragmagraph serve --workspace <workspace-dir>`

The service is deliberately local-first and single-process. The package also
ships a bounded MCP stdio adapter over this service. It does not claim HTTP,
hosted transport, background watching, auth, or daemon supervision.

Capabilities and health responses are intentionally richer than the MVP surface:

- snapshot identity
- workspace path when workspace-backed
- manifest schema version
- parser set
- parser versions
- export and report format support
- refresh support posture
- diagnostic counts
- git overlay support posture
- git identity mode
- git commit and changed-path counts
- explicit refresh readiness and artifact-presence facts

## Request envelope

One JSON object per line:

```json
{"id":"req-1","method":"query","params":{"text":"RuntimeGraph","max_results":5}}
```

## Response envelope

Success:

```json
{"id":"req-1","ok":true,"result":{"query":"RuntimeGraph","hits":[],"omitted":[],"diagnostics":{},"next_cursor":""}}
```

Failure:

```json
{"id":"req-1","ok":false,"error":{"code":"invalid_params","message":"max_results must be >= 1","details":{"max_results":0}}}
```

## Supported methods

- `capabilities`
- `health`
- `status`
- `query`
- `explain`
- `neighborhood`
- `path`
- `report`
- `export`
- `graphify_export`
- `refresh` (root-backed and workspace-backed startup only)
- `shutdown`

Root-backed and workspace-backed `refresh` responses include deterministic
`path_changes`, `snapshot_delta`, `identity_transitions`, `work`, and `health`
summaries. `neighborhood` and `path` accept optional `edge_kinds` and
`node_kinds` arrays; omitted filters preserve the original behavior.
`query` and `explain` accept optional `cursor` and `max_examined` values.
`export` accepts `profile` with `full`, `no_content`, `no_identities`, or
`portable`.

`status` returns a compact machine-readable readiness view for clients and UI
surfaces that need to know what is currently loaded and whether an explicit
refresh can run:

- startup mode and namespace
- snapshot identity and graph counts
- root, snapshot, workspace, and store paths when present
- artifact presence for snapshot, manifest, refresh-status, cache, store, and
  workspace files
- refresh readiness with a deterministic reason such as
  `root_backed_explicit_refresh_available`,
  `workspace_explicit_refresh_available`,
  `snapshot_backed_refresh_unsupported`, or
  `store_backed_refresh_unsupported`
- last refresh ledger facts when available

`pragmagraph doctor` combines this status payload with deterministic query
evidence, materialized-store search explanation when a store is supplied, and a
read-only store export comparison. It can also write the same evidence JSON and
a compact Markdown agent-context handoff used by the local evidence workbench.

## MCP resources

`pragmagraph-server serve-stdio` exposes the existing tools plus read-only
`pragma://status`, `pragma://snapshot`, `pragma://report`, and
`pragma://node/{node_id}` resources. `pragma://status` includes the same
service `status` payload alongside capabilities and snapshot statistics.
Listing and reading resources reuse the already-loaded service state and never
trigger refresh or semantic inference.

## Boundary

The service only returns deterministic structural facts derived from the loaded
snapshot or indexed root. It does not perform LLM inference, memory writes, or
OpenMinion runtime wiring.

When the loaded snapshot contains git overlays, capabilities and health payloads
surface only observed git facts and the active privacy posture:

1. commit/path counts,
2. whether git overlays are enabled,
3. the active identity mode (`name_email_hash` by default, `full` only when
   explicitly enabled).
