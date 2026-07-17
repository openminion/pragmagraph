# Advanced Ingestion And Interchange

Status: semantic alpha
Scope: bounded observed-fact ingestion and read-only consumption surfaces

## Query pagination

`QueryRequest` accepts `cursor` and `max_examined`. Cursors are opaque,
request-bound, deterministic continuation tokens. A work budget is an admission
limit: when the backend cannot produce canonical ranking inside the budget, it
returns `work_budget_exhausted` with honest counts instead of approximate hits.

## Multi-root composition

`pragmagraph.workspace.index_multi_root(...)` composes explicitly named
`WorkspaceRoot` values. Root names and namespaces must be unique. Output is
independent of argument order and every imported fact carries `workspace_root`
metadata. Refresh remains explicit; this helper does not watch roots.

```python
from pragmagraph.workspace import WorkspaceRoot, index_multi_root

snapshot = index_multi_root(
    (
        WorkspaceRoot("api", "../api"),
        WorkspaceRoot("web", "../web"),
    )
)
```

## Artifact and dependency facts

The local indexer recognizes observed structure in:

1. OpenAPI JSON and bounded YAML syntax,
2. protobuf messages, services, and RPCs,
3. SQL tables and statement-local foreign-key references,
4. Terraform resource, data, module, and provider blocks,
5. GitHub Actions jobs and `uses` references,
6. Python and npm manifests, requirements files, and lockfiles.

Manifest declarations and lockfile resolutions are separate nodes connected by
`resolves_to` only when ecosystem and package name match exactly. Missing
resolutions and malformed artifacts are diagnostics, not inferred facts.

## Precise code-intelligence interchange

`pragmagraph.interchange` exposes three exact-fact paths:

1. `snapshot_from_compiler_facts(...)` accepts caller-produced symbol and
   reference DTOs with source ranges.
2. `snapshot_to_scip_json(...)` and `snapshot_from_scip_json(...)` implement a
   documented JSON subset of SCIP metadata, documents, symbols, occurrences,
   definition/reference roles, and ranges.
3. `load_native_scip(...)` and `snapshot_from_scip_protobuf(...)` consume a
   bounded native protobuf subset when the optional `scip` extra is installed.
   `merge_precise_snapshot(...)` composes those facts with an existing snapshot
   by exact IDs only.

The package does not launch compilers or language servers and does not claim
full SCIP compatibility. Unsupported, malformed, and unknown fields are
reported through the ingestion loss report. See
[`native-scip-ingestion.md`](native-scip-ingestion.md) for the accepted field,
freshness, privacy, and producer-certification contract.

## CI delta

`build_ci_delta(before, after, fail_on_changes=...)` compares canonical node,
edge, omission, and snapshot-level facts. It reports added, removed, and
payload-changed IDs plus changed snapshot fields such as ingestion stats.
The optional exit policy is structural only; it does not label changes risky or
recommend action.

## Export redaction

`project_snapshot(...)` derives an export without mutating canonical truth:

- `full`: current full-fidelity behavior
- `no_content`: removes node text, labels, and content-like metadata
- `no_identities`: removes author and committer identity metadata
- `portable`: removes the machine-local snapshot root while keeping relative
  source paths; native SCIP project/workspace roots are also removed

The `pragmagraph export` command and local service `export` method accept the
same profile names.

## MCP resources

The in-package `pragmagraph-server` exposes read-only resources over its loaded
service instance:

- `pragma://status`
- `pragma://snapshot`
- `pragma://report`
- `pragma://precise-ingestion`
- `pragma://node/{node_id}`

Use `resources/list`, `resources/templates/list`, and `resources/read` through
an MCP client. Existing MCP tools remain backward compatible. Resources do not
refresh, mutate, summarize, or classify graph facts.
