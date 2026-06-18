# Service Mode

PragmaGraph now ships a package-owned local service surface for repeated graph
queries without reloading state on every call.

## Public root

- `pragmagraph.service`

## CLI entrypoints

- `pragmagraph serve --snapshot <snapshot.json>`
- `pragmagraph serve --root <repo-root> --namespace <name>`
- `pragmagraph serve --workspace <workspace-dir>`

The service is deliberately local-first and single-process. It does not claim
HTTP, MCP, hosted transport, background watching, auth, or daemon supervision.

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

## Request envelope

One JSON object per line:

```json
{"id":"req-1","method":"query","params":{"text":"RuntimeGraph","max_results":5}}
```

## Response envelope

Success:

```json
{"id":"req-1","ok":true,"result":{"query":"RuntimeGraph","hits":[],"omitted":[],"diagnostics":{}}}
```

Failure:

```json
{"id":"req-1","ok":false,"error":{"code":"invalid_params","message":"max_results must be >= 1","details":{"max_results":0}}}
```

## Supported methods

- `capabilities`
- `health`
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
`path_changes`, `snapshot_delta`, and `health` summaries so callers can inspect
structural change without reparsing the whole service response by hand.

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
