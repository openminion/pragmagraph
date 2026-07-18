<p align="center">
  <img src="https://www.openminion.com/brand/openminion-logo.png" alt="OpenMinion logo" width="128" />
</p>

<h1 align="center">PragmaGraph</h1>

<p align="center">
  <strong>Standalone observed-fact graph substrate for code and document structure.</strong>
</p>

<p align="center">
  <a href="https://github.com/openminion/pragmagraph">GitHub</a>
  · <a href="https://pypi.org/project/pragmagraph/">PyPI</a>
  · <a href="https://www.openminion.com">Website</a>
  · <a href="https://x.com/OpenMinion">X</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/pragmagraph/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-v0.0.5-3775A9"></a>
  <a href="https://pypi.org/project/pragmagraph/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/pragmagraph"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-published%20alpha-5B8DEF">
</p>

`pragmagraph` is a standalone observed-fact graph substrate for code and
document structure. The name comes from Greek `pragma` (`πρᾶγμα`), meaning a
deed, matter, fact, or thing done; in this package it frames the third brain as
a graph of reproducible structure: files, symbols, document sections, artifacts,
references, commits, and other facts an indexer can recover from source.

Use it when you want reproducible code, docs, git, and artifact facts that an
indexer can recover without an LLM.

This semantic alpha includes deterministic DTOs, JSON snapshots, local
code/document indexing, refresh manifests, structural deltas, query helpers,
local service contracts, MCP tools and read-only resources, reports, exports,
Graphify-shaped interop, loss-aware SCIP JSON and native protobuf intake,
exact cross-repository symbol resolution, benchmark helpers, and CLI commands
for observed-fact graph work.

## Trust and Brand Safety

- Official GitHub: `https://github.com/openminion/pragmagraph`
- Official website: `https://www.openminion.com`
- Official X account: `https://x.com/OpenMinion`

`pragmagraph` has no official token, coin, NFT, airdrop, staking program,
treasury product, or investment offering. Any claim otherwise is unauthorized
and should be treated as a scam.

## At a glance

- Current public package line: `0.0.5` alpha
- Best fit when: you want reproducible code, docs, git, and artifact facts that
  an indexer can recover without an LLM
- Public shape: deterministic DTOs, local indexing, query/report/export
  helpers, refresh manifests, and package-local service/workspace/UI preview
  contracts
- Relationship to the rest of the family: PragmaGraph is the observed-fact
  graph lane; Sophiagraph remains the durable-memory lane
- Not the claim: no hosted service, prompt orchestration, memory promotion, or
  implicit runtime-side inference lives here
- Preferred package validation gate: `make check`, with `make release-check`
  for release proof

## What PragmaGraph provides

The package currently provides:

- Core graph contracts: stable alpha import roots centered on `pragmagraph`,
  `contracts`, `models`, `query`, `storage`, `adapters`, `refresh`, `report`,
  `service`, and `workspace`, plus immutable DTOs for refs, nodes, edges,
  snapshots, queries, diagnostics, and health
- Indexing: deterministic JSON snapshots and a local indexer for files,
  Markdown structure, Python AST facts, TypeScript/JavaScript structure,
  selected config metadata, OpenAPI, protobuf, SQL schema, Terraform, CI
  workflows, manifests/lockfiles, snippets, and git-history overlays
- Query and refresh: neighborhood/path/explain/impact helpers, reverse-edge
  lookups, content-hash refresh manifests, structural deltas, saved refresh
  profiles, explicit refresh state reporting, compact repo-map handoffs, and
  query-plan evidence, plus deterministic query cursors and work budgets
- Storage interchange: canonical JSON snapshot stores, local SQLite
  materialized stores, typed store manifests, capability reports, import/export
  commands, and store-backed query/service routing
- Reports, export, and interop: structural reports, DOT/Mermaid export,
  export-time redaction profiles, Graphify-shaped JSON interchange, stable
  symbol/reference interchange, a loss-aware SCIP JSON subset, optional native
  SCIP protobuf intake, caller-fed compiler/LSP facts,
  topology/doc-graph views, git lineage, parser-support metadata, and
  certification packs
- Cross-repository navigation: deterministic composition of caller-named
  canonical snapshots, complete package/version-aware SCIP identity matching,
  ordinary `resolves_to` edges for one exact provider definition, and bounded
  typed diagnostics for missing, ambiguous, malformed, same-root, or
  version-mismatched identities
- Viewer contract: bounded `pragmagraph.viewer` envelopes for GraphFakos and
  other provider-neutral graph viewers, including clusters, LOD, edge bundles,
  omitted counts, content previews, evidence, provenance, and deterministic
  1k/200k/1m fixture generation
- Local runtime surfaces: stdio query service contracts, MCP tools and read-only
  resources, single- and multi-root workspace helpers, `serve --workspace`,
  and the package-local visual preview boundary under `pragmagraph.ui`
- Operational support: benchmark helpers, repo-local regression fixtures,
  gitignore-aware indexing/security rules, CLI commands, install smoke, and
  compatibility/release docs

### Package boundary

`pragmagraph` is the observed-fact graph lane in the OpenMinion family:

- **Sophiagraph** owns inferred, judged, lossy durable memory.
- **PragmaGraph** owns observed, indexer-extracted, reproducible facts and
  deeds.
- **Graphify** remains a third-brain adapter. **PragmaGraph** is the native
  package surface for OpenMinion's observed-fact graph lane, not a relabeling
  of Graphify.

Practical rule: if a parser, static analyzer, doc walker, git reader, or shell
command can reproduce the fact without an LLM, it belongs in PragmaGraph. If it
depends on a preference, operator pin, summary, design judgment, or memory
consolidation decision, it belongs in Sophiagraph. Sophiagraph may cite
PragmaGraph with `pragma://...` evidence references; PragmaGraph never stores
Sophiagraph's judgments.

### Package vs service ownership for indexing, service mode, and UI preview

`pragmagraph` (this package) is the typed contract, deterministic indexer, and
local execution surface for observed-fact graph work. It exposes:

- reproducible DTOs, snapshot models, query helpers, and report/export surfaces
- package-local indexing, refresh manifests, structural deltas, and workspace
  helpers
- stdio service contracts, local preview boundaries in `pragmagraph.ui`, and
  deterministic standalone smoke validation

`pragmagraph` does **not** own a hosted service, browser-session runtime,
OpenMinion orchestration, or long-running operators. Those belong to a host
runtime or follow-on service layer. The package supplies the typed contract and
deterministic local behavior; the host supplies operational runtime behavior.

## What PragmaGraph does not provide

This package does **not** currently provide:

- KuzuDB, Neo4j, hosted, vector, or typed-edge storage
- Graphify runtime API wrapping or Graphify replacement behavior
- file watchers, git hooks, daemons, or scheduled refresh
- HTTP, WebSocket, or hosted service transports
- OpenMinion runtime provider wiring
- prompt context merging
- the actual hosted operator-facing workbench runtime UI (that belongs to
  OpenMinion; `pragmagraph.ui` owns the package adapter and typed boundary,
  while GraphFakos owns the shared local viewer shell)
- semantic inference from prose or model output
- automatic Sophiagraph memory writes or promotion

Those features belong to follow-on releases or to OpenMinion's provider
adapter layer.

The current visual explorer command lives in `pragmagraph.ui` and renders
through GraphFakos, the shared graph lens package. PragmaGraph owns the
observed-fact adapter and graph semantics; GraphFakos owns the reusable viewer
shell, graph canvas, local server primitive, and static export surface.

For large viewer iteration, generate a bounded PragmaGraph viewer envelope and
open it through GraphFakos:

```bash
pragmagraph viewer-fixture \
  --scenario viewer-scale-200k \
  --out .pragmagraph/viewer-fixtures/viewer-scale-200k.json \
  --json
```

See [`docs/viewer-contract.md`](docs/viewer-contract.md) for the envelope,
cluster, content, fixture, and GraphFakos handoff contract.

You can run the package-local visual UI today:

```bash
pragmagraph-ui \
  --screen search \
  --serve \
  --open
```

Use a persistent workspace as the preview source:

```bash
pragmagraph-ui \
  --workspace <workspace-root> \
  --screen provider_status \
  --serve
```

Use `--html-out` only when you want to export a standalone HTML snapshot. The
equivalent module form is `python3.11 -m pragmagraph ui-preview`.

## CLI Quickstart

Index a local code/docs root into a deterministic JSON snapshot:

```bash
pragmagraph index . \
  --out .pragmagraph/snapshot.json \
  --namespace my-project \
  --git-identity-mode name_email_hash \
  --json
```

Query the snapshot:

```bash
pragmagraph query .pragmagraph/snapshot.json "RuntimeGraph" --json
```

Continue a bounded query page using the returned `next_cursor`:

```bash
pragmagraph query .pragmagraph/snapshot.json "RuntimeGraph" \
  --max-results 25 \
  --cursor '<next_cursor>' \
  --max-examined 100000 \
  --json
```

Compose several named roots or compare two snapshots in CI:

```bash
pragmagraph multi-root-index \
  --root api=../api \
  --root web=../web \
  --out .pragmagraph/workspace.json \
  --json

# Compose already-built precise snapshots without reindexing source.
pragmagraph multi-root-compose \
  --snapshot api=.pragmagraph/api.json \
  --snapshot web=.pragmagraph/web.json \
  --out .pragmagraph/precise-workspace.json \
  --json

pragmagraph ci-delta before.json after.json --fail-on-changes --json
```

`multi-root-compose` preserves each input ID and fact, adds explicit root
provenance, and resolves an external SCIP symbol only when exactly one defining
node in another named root has the same complete symbol and package version.
It never falls back to labels, paths, package-name similarity, version ranges,
or network lookup. The command writes atomically; failed validation leaves an
existing destination unchanged. The composed file is derived and can be
deleted and rebuilt from its unchanged input snapshots.

The output records a stable SHA-256 digest for each canonical input snapshot.
Treat those digests and producer metadata according to the same sharing policy
as the source snapshots. Resolution itself adds no inferred intent, personal
profile, source content, or memory record.

Refresh and explain with deterministic metadata:

```bash
pragmagraph refresh . \
  --out .pragmagraph/snapshot.json \
  --manifest-out .pragmagraph/manifest.json \
  --namespace my-project \
  --json

pragmagraph explain .pragmagraph/snapshot.json "RuntimeGraph" --json
```

Inspect git-aware provenance:

```bash
pragmagraph git-commits-for-path .pragmagraph/snapshot.json src/app.py --json
pragmagraph git-files-for-commit .pragmagraph/snapshot.json abc123def456 --json
pragmagraph git-commits-for-symbol \
  .pragmagraph/snapshot.json \
  "pragma://my-project/python_class/src/app.py:RuntimeGraph" \
  --json
```

## Install

Install from PyPI:

```bash
python3.11 -m pip install pragmagraph
```

Editable install during local development:

```bash
python3.11 -m pip install -e .
```

Install with development tools:

```bash
python3.11 -m pip install -e ".[dev]"
```

Install with the optional precise TypeScript/JavaScript parser family:

```bash
python3.11 -m pip install -e ".[precise]"
```

Install native SCIP protobuf intake support:

```bash
python3.11 -m pip install -e ".[scip]"
```

Import an externally produced `index.scip` file:

```bash
pragmagraph precise-import index.scip \
  --root . \
  --namespace my-project \
  --out precise-snapshot.json \
  --json
```

Add `--base snapshot.json` to compose precise facts with an existing canonical
snapshot. PragmaGraph reads the file but never installs, discovers, or launches
an external indexer.

Wheel build:

```bash
python3.11 -m build
```

## Standalone Smoke

Source-root smoke:

```bash
PYTHONPATH=src python3.11 -m pragmagraph --json
```

Installed-console-script smoke:

```bash
pragmagraph-smoke --json
```

Expected output is deterministic JSON with the package name, version, status,
stable import roots, and `semantic_contract: true`.

## Docs and release

- `docs/README.md` summarizes the package-local docs contract.
- `API_COMPATIBILITY.md` records the supported public import roots and
  top-level export policy.
- `RELEASING.md` records the package-local release and PyPI publish flow.
- `docs/service-mode.md` records the local service request/response
  contract, including parser provenance in capabilities and health payloads.
- `docs/workspace-mode.md` records the persistent local workspace
  contract.
- `docs/refresh-operations.md` records the package-owned explicit
  refresh/profile/status contract.
- `docs/report-mode.md` records the structural report contract.
- `docs/export-mode.md` records the deterministic export contract.
- `docs/graphify-interop.md` records the deterministic Graphify
  interchange contract.
- `docs/benchmarking.md` records the benchmark surface and readiness
  posture.
- `docs/git-history-mode.md` records the local git-overlay contract,
  privacy posture, and CLI shape.
- `docs/advanced-structural-views.md` records symbol/reference interchange,
  topology, document-graph, query-plan, git-lineage, parser-support, and
  certification helper surfaces.
- `docs/native-scip-ingestion.md` records the bounded native SCIP
  field subset, explicit CLI, freshness, privacy, and certification posture.
- `docs/ui-contracts.md` records the package-owned UI boundary
  contract.
- `docs/source-tree-owner-map.md` explains the source-tree module
  layout and public-vs-repo-local boundary.
- `scripts/release_check.py` is the canonical release smoke entrypoint.
- `tests/fixtures/repos/` and `tests/contracts/` hold repo-local regression
  fixtures and OpenMinion contract snapshots; they are validation assets, not
  public package API.

Inspect nearby graph facts:

```bash
pragmagraph neighborhood .pragmagraph/snapshot.json \
  "pragma://my-project/file/src/app.py" --json
```

Check health:

```bash
pragmagraph health .pragmagraph/snapshot.json --json
```

Inspect impact and reverse edges:

```bash
pragmagraph neighborhood .pragmagraph/snapshot.json \
  "pragma://my-project/module/src/app.py" \
  --edge-kind imports \
  --json
```

Run the local query service against a saved snapshot:

```bash
pragmagraph serve --snapshot .pragmagraph/snapshot.json
```

Build and query a local SQLite materialized store:

```bash
pragmagraph store-import .pragmagraph/snapshot.json \
  --out .pragmagraph/graph.sqlite

pragmagraph store-query .pragmagraph/graph.sqlite RuntimeGraph --json

pragmagraph store-health .pragmagraph/graph.sqlite --json
```

Run the local query service against the materialized store:

```bash
pragmagraph serve --store .pragmagraph/graph.sqlite
```

Open the local visual UI against a saved snapshot:

```bash
pragmagraph-ui \
  --snapshot .pragmagraph/snapshot.json \
  --screen search \
  --serve \
  --open
```

Run the local query service against a repo root with explicit refresh support:

```bash
pragmagraph serve --root . --namespace my-project
```

Preview what an explicit refresh would touch:

```bash
pragmagraph refresh-plan . --manifest-in .pragmagraph/manifest.json --json
```

Create and run a repeatable explicit-refresh profile:

```bash
pragmagraph profile-init . \
  --out .pragmagraph/profile.json \
  --label my-project \
  --namespace my-project \
  --snapshot-out .pragmagraph/snapshot.json \
  --manifest-out .pragmagraph/manifest.json \
  --state-out .pragmagraph/status.json \
  --json

pragmagraph profile-run .pragmagraph/profile.json --json
pragmagraph refresh-status .pragmagraph/status.json --json
```

Build a structural report:

```bash
pragmagraph report .pragmagraph/snapshot.json

pragmagraph report .pragmagraph/snapshot.json --json
```

Export graph text:

```bash
pragmagraph export .pragmagraph/snapshot.json --format dot

pragmagraph export .pragmagraph/snapshot.json --format mermaid
```

Benchmark a local repo:

```bash
pragmagraph benchmark /path/to/repo --namespace demo --query RuntimeGraph

pragmagraph benchmark /path/to/repo \
  --namespace demo \
  --query RuntimeGraph \
  --json
```

Export and import Graphify-shaped JSON:

```bash
pragmagraph graphify-export .pragmagraph/snapshot.json > graphify.json

pragmagraph graphify-import graphify.json --out .pragmagraph/imported.json
```

## External Consumer Quickstart

Minimal standalone flow for another framework or service:

```python
import pragmagraph

snapshot = pragmagraph.index_path(".", namespace="example")
pragmagraph.save_snapshot(snapshot, ".pragmagraph/snapshot.json")
print(pragmagraph.PACKAGE_STATUS)
```

The package can also be checked from a shell:

```bash
python3.11 -m pragmagraph --json
```

Workspace quickstart:

```bash
pragmagraph workspace-init /path/to/repo --workspace .pragmagraph-workspace --json
```

Library consumers that want the typed workspace helpers can also import
`pragmagraph.workspace` directly.

Workspace visual UI:

```bash
pragmagraph-ui --workspace .pragmagraph-workspace --screen provider_status --serve
```

Reference docs:

- [API_COMPATIBILITY.md](API_COMPATIBILITY.md) — public import-root policy.
- [docs/report-mode.md](docs/report-mode.md) — structural report contract.
- [docs/export-mode.md](docs/export-mode.md) — deterministic graph exports.
- [docs/benchmarking.md](docs/benchmarking.md) — benchmark/readiness surface.
- [docs/storage-interchange.md](docs/storage-interchange.md) — canonical
  snapshot and materialized store contract.
- [docs/graphify-interop.md](docs/graphify-interop.md) — Graphify-shaped JSON
  interchange.
- [docs/workspace-mode.md](docs/workspace-mode.md) — persistent local workspace
  contract.
- [docs/certification-readiness-matrix.md](docs/certification-readiness-matrix.md)
  — package/OpenMinion proof coverage.
- [RELEASING.md](RELEASING.md) — package-local release checks.

## License and brand-use boundary

- Source code license: `Apache-2.0`
- Brand/trademark grant: `none`

The software license grants rights to use, modify, and redistribute the code.
It does **not** grant rights to use the PragmaGraph, Sophiagraph, or OpenMinion
names, logos, branding, website identity, or social identity except for
truthful attribution. Forks, clones, and derivative distributions must not
present themselves as the official PragmaGraph project or imply affiliation,
endorsement, or maintenance by PragmaGraph or OpenMinion contributors unless
that is actually true.
