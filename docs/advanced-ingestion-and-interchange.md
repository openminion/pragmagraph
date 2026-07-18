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

### Exact cross-repository composition

`compose_snapshots(...)` and `multi-root-compose` operate on already-built
canonical snapshots. They do not reindex source. Each input keeps its IDs and
facts, receives explicit `workspace_root` provenance, and is recorded in a
sorted manifest with the SHA-256 digest of its canonical JSON payload.

```python
from pragmagraph.storage import load_snapshot
from pragmagraph.workspace import NamedSnapshot, compose_snapshots

result = compose_snapshots(
    (
        NamedSnapshot("api", load_snapshot("api.json")),
        NamedSnapshot("web", load_snapshot("web.json")),
    )
)
```

An external SCIP node receives a cross-root `resolves_to` edge only when one
definition in another named root has the same complete producer-supplied SCIP
symbol, including package manager, package name, package version, and escaped
descriptor sequence. Missing, malformed, ambiguous, same-root, and
version-mismatched identities add no guessed edge. Their exact aggregate counts
and bounded details remain in `stats.cross_repo_resolution` and `omitted`.

The output uses the current snapshot/indexer envelope, an empty `root_path`, and
no implicit wall-clock timestamp. Duplicate roots, namespaces, IDs, nested
composition, unsupported schemas, invalid project counts, and dangling edges
fail before output. CLI replacement is atomic, so rollback means retaining or
restoring the prior derived output; input snapshots are never mutated.

The local service and MCP server may read a composed snapshot and expose its
ordinary facts and stats. They do not gain a compose method, tool, write
resource, watcher, registry lookup, or transport. GraphFakos owns shared visual
navigation, Sophiagraph owns durable judged memory, and OpenMinion owns runtime
provider/context orchestration.

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

The loss-aware SCIP JSON subset cannot represent composed cross-root
`resolves_to` edges. Export reports them explicitly as
`omitted_cross_repo_resolution_count`; it never drops them silently. Stable
PragmaGraph symbol/reference bundles and Graphify payloads preserve the edge.

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
