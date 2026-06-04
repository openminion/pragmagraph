# Service Mode

PragmaGraph now ships a package-owned local service surface for repeated graph
queries without reloading state on every call.

## Public root

- `pragmagraph.service`

## CLI entrypoints

- `pragmagraph serve --snapshot <snapshot.json>`
- `pragmagraph serve --root <repo-root> --namespace <name>`

The service is deliberately local-first and single-process. It does not claim
HTTP, MCP, hosted transport, background watching, auth, or daemon supervision.

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
- `refresh` (root-backed startup only)
- `shutdown`

## Boundary

The service only returns deterministic structural facts derived from the loaded
snapshot or indexed root. It does not perform LLM inference, memory writes, or
OpenMinion runtime wiring.
