<p align="center">
  <img src="https://www.openminion.com/brand/openminion-logo.png" alt="PragmaGraph logo" width="128" />
</p>

<h1 align="center">PragmaGraph</h1>

<p align="center">
  <strong>Deterministic observed-fact graphs for code, docs, artifacts, and Git history.</strong>
</p>

<p align="center">
  <a href="https://github.com/openminion/pragmagraph">GitHub</a>
  · <a href="https://pypi.org/project/pragmagraph/">PyPI</a>
  · <a href="https://www.openminion.com">Website</a>
  · <a href="docs/README.md">Docs</a>
  · <a href="https://x.com/OpenMinion">X</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/pragmagraph/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-v0.0.7rc1-3775A9"></a>
  <a href="https://pypi.org/project/pragmagraph/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/pragmagraph?cacheSeconds=300"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-6B7280">
</p>

PragmaGraph `v0.0.7rc1` is a standalone semantic-alpha package for facts that can
be reproduced from source. It indexes local code, documents, artifacts, and
Git history into deterministic graph snapshots without asking an LLM to decide
what is true.

## Read This First

1. Read [At a Glance](#at-a-glance) to confirm the observed-fact boundary.
2. Follow [Install](#install) and [Quick Start](#quick-start) to index and query
   one local project.
3. Read [How It Fits](#how-it-fits) before mixing observed facts with durable
   memory or a graph viewer.
4. Use the [Ten Minute Tour](docs/ten-minute-tour.md) for the complete
   workspace, viewer, store, certification, and refresh path.
5. Read [Development](#development) before changing the package.

## Trust and Brand Safety

- Official GitHub: <https://github.com/openminion/pragmagraph>
- Official website: <https://www.openminion.com>
- Official X account: <https://x.com/OpenMinion>

PragmaGraph has no official token, coin, NFT, airdrop, staking program,
treasury product, or investment offering. Any claim otherwise is unauthorized
and should be treated as a scam.

## At a Glance

| | |
| --- | --- |
| Package | `pragmagraph` |
| Current line | `v0.0.7rc1` semantic alpha |
| Python | 3.11+ |
| Best fit | Reproducible source, document, artifact, and Git facts |
| Primary artifact | Deterministic JSON graph snapshot |
| Main surfaces | Index, query, refresh, report, export, workspace, service, and viewer adapter |
| Not the claim | Semantic inference, durable agent memory, or hosted graph infrastructure |

Practical rule: if a parser, static analyzer, document walker, Git reader, or
explicit command can reproduce a fact without an LLM, it belongs in
PragmaGraph.

## Common Commands

```bash
python3.11 -m pip install pragmagraph
pragmagraph-smoke --json
pragmagraph index . --out .pragmagraph/snapshot.json --namespace demo --json
pragmagraph query .pragmagraph/snapshot.json "RuntimeGraph" --json
pragmagraph-ui --serve --open --json
```

## Install

Install the base package:

```bash
python3.11 -m pip install pragmagraph
```

Optional precise parser and native SCIP support:

```bash
python3.11 -m pip install "pragmagraph[precise]"
python3.11 -m pip install "pragmagraph[scip]"
```

For a source checkout:

```bash
python3.11 -m pip install -e ".[dev]"
python3.11 -m pip install -e ".[precise]"
python3.11 -m pip install -e ".[scip]"
```

## Quick Start

### External Consumer Quickstart

Index a local project:

```bash
pragmagraph index . \
  --out .pragmagraph/snapshot.json \
  --namespace demo \
  --git-identity-mode name_email_hash \
  --json
```

Query the snapshot:

```bash
pragmagraph query .pragmagraph/snapshot.json "RuntimeGraph" --json
```

Refresh it explicitly:

```bash
pragmagraph refresh . \
  --out .pragmagraph/snapshot.json \
  --manifest-out .pragmagraph/manifest.json \
  --namespace demo \
  --json
```

Run the package example:

```bash
python3.11 examples/basic_usage.py
```

For a reusable workspace and local visual graph, continue with
[`docs/ten-minute-tour.md`](docs/ten-minute-tour.md).

## Command Map

The quickstart above is the shortest useful path. These grouped commands make
the broader public surface easier to discover without requiring a full CLI
reference read.

Inspect, export, and benchmark a snapshot:

```bash
pragmagraph report .pragmagraph/snapshot.json --json
pragmagraph export .pragmagraph/snapshot.json --format mermaid
pragmagraph graphify-export .pragmagraph/snapshot.json > graphify.json
pragmagraph benchmark .
```

Follow observed Git provenance:

```bash
pragmagraph git-commits-for-path .pragmagraph/snapshot.json src/app.py --json
pragmagraph git-files-for-commit .pragmagraph/snapshot.json abc123def456 --json
pragmagraph git-commits-for-symbol \
  .pragmagraph/snapshot.json RuntimeGraph --json
```

Import precise SCIP facts explicitly:

```bash
pragmagraph precise-import index.scip \
  --root . --namespace demo --out precise-snapshot.json --json
```

Operate a workspace or materialized store:

```bash
pragmagraph workspace-init . \
  --workspace .pragmagraph/workspace --json
pragmagraph workspace-query .pragmagraph/workspace RuntimeGraph --json
pragmagraph store-search-explain \
  .pragmagraph/graph.sqlite RuntimeGraph --json
pragmagraph certify .pragmagraph/snapshot.json --json
pragmagraph serve --snapshot .pragmagraph/snapshot.json
```

## What PragmaGraph Provides

- immutable graph DTOs for nodes, edges, source references, queries, and
  snapshots
- deterministic indexing for code, Markdown, selected configuration, schemas,
  manifests, CI workflows, and Git history
- explicit refresh manifests, structural deltas, and CI comparisons
- neighborhood, path, reverse-edge, impact, explanation, and query-plan helpers
- JSON and SQLite-backed storage interchange
- reports plus JSON, Markdown, DOT, Mermaid, Graphify, and SCIP-oriented
  interchange
- multi-root composition and exact cross-repository symbol resolution
- workspace, local service, read-only MCP, benchmark, certification, and
  privacy surfaces
- a provider adapter for GraphFakos and package-owned visual preview commands

## What PragmaGraph Does Not Provide

- LLM-based fact extraction or semantic judgment
- durable agent memory, memory promotion, or preference storage
- implicit background watchers, Git hooks, cron jobs, or daemons
- hosted HTTP, WebSocket, indexing, or collaboration infrastructure
- OpenMinion orchestration or prompt-context merging
- ownership of GraphFakos viewer behavior
- automatic execution of external indexers

Refresh, ingestion, and precise-fact import are explicit. The package does not
silently install tools, start background workers, or perform network discovery.

## How It Fits

| Package | Responsibility |
| --- | --- |
| OpenMinion | Agent runtime, turns, tools, sessions, and orchestration |
| SophiaGraph | Durable memory, provenance, lifecycle, and workspace knowledge |
| PragmaGraph | Deterministic observed facts from source and artifacts |
| GraphFakos | Provider-neutral graph viewing and interaction contracts |

SophiaGraph may cite a PragmaGraph fact as evidence. PragmaGraph does not store
SophiaGraph’s summaries, preferences, judgments, or memory decisions.
GraphFakos may render a PragmaGraph projection but does not become the owner of
the source facts.

## Workspaces, Interchange, and Viewing

Create a reusable workspace configuration:

```bash
pragmagraph workspace-config-init . \
  --out .pragmagraph/workspace.toml \
  --workspace .pragmagraph/workspace \
  --label demo \
  --namespace demo \
  --ui-screen project_health \
  --json
```

Open the visual graph:

```bash
pragmagraph demo-ui \
  --config .pragmagraph/workspace.toml \
  --serve --open --json
```

PragmaGraph owns observed-fact semantics and the adapter payload. GraphFakos
owns the reusable viewer shell. See
[`docs/viewer-contract.md`](docs/viewer-contract.md) and
[`docs/storage-interchange.md`](docs/storage-interchange.md) before integrating
either boundary.

Stable consumer owners are exposed under `pragmagraph.workspace` and
`pragmagraph.ui`; use those package surfaces rather than reaching into CLI
implementation modules.

## Development

```bash
make dev-install
make hooks-install
make check
```

Use `make release-check` before publishing or changing the documented public
surface.

## Docs and Release

- [`docs/README.md`](docs/README.md): package documentation map
- [`docs/ten-minute-tour.md`](docs/ten-minute-tour.md): shortest complete tour
- [`docs/standalone-product-cycle.md`](docs/standalone-product-cycle.md):
  end-to-end local product cycle
- [`docs/refresh-operations.md`](docs/refresh-operations.md): refresh and
  status contracts
- [`docs/service-mode.md`](docs/service-mode.md): local service boundary
- [`docs/workspace-mode.md`](docs/workspace-mode.md): persistent workspace
  contract
- [`docs/source-tree-owner-map.md`](docs/source-tree-owner-map.md): code owners
  and package layout
- [`API_COMPATIBILITY.md`](API_COMPATIBILITY.md): supported import roots
- [`RELEASING.md`](RELEASING.md): release and publish flow

## License and Brand-use Boundary

- Source code license: Apache-2.0
- Brand/trademark grant: none

The license grants rights to use, modify, and redistribute the code. It does
not grant rights to present a fork, clone, token, website, or social account as
the official PragmaGraph or OpenMinion project or imply affiliation or
endorsement.
