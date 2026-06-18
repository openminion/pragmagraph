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
  <a href="https://pypi.org/project/pragmagraph/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pragmagraph?color=3775A9"></a>
  <a href="https://pypi.org/project/pragmagraph/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/pragmagraph"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-published%20alpha-5B8DEF">
</p>

`pragmagraph` is a standalone observed-fact graph substrate for code and
document structure. The name comes from Greek `pragma` (`πρᾶγμα`), meaning a
deed, matter, fact, or thing done; in this package it frames the third brain as
a graph of reproducible structure: files, symbols, document sections, artifacts,
references, commits, and other facts an indexer can recover from source.

This semantic alpha provides a local observed-fact source-graph surface:
deterministic DTOs, JSON snapshots, a local code/document indexer, incremental
refresh manifests and structural deltas, structural query helpers, a local
query service surface, deterministic graph reports and exports, Graphify-shaped
interop, benchmark helpers, and CLI commands for local observed-fact graph
work.

## Boundary

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

## Trust and Brand Safety

- Official GitHub: `https://github.com/openminion/pragmagraph`
- Official PyPI: `https://pypi.org/project/pragmagraph/`
- Official website: `https://www.openminion.com`
- Official X account: `https://x.com/OpenMinion`

`pragmagraph` has no official token, coin, NFT, airdrop, staking program,
treasury product, or investment offering. Any claim otherwise is unauthorized
and should be treated as a scam.

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

## What the package provides

The package currently provides:

- package metadata and Apache-2.0 release files
- stable alpha import roots:
  - `pragmagraph`
  - `pragmagraph.contracts`
  - `pragmagraph.models`
  - `pragmagraph.query`
  - `pragmagraph.storage`
  - `pragmagraph.adapters`
  - `pragmagraph.bench`
  - `pragmagraph.portability`
  - `pragmagraph.parsers`
  - `pragmagraph.export`
  - `pragmagraph.graphify`
  - `pragmagraph.report`
  - `pragmagraph.refresh`
  - `pragmagraph.operations`
  - `pragmagraph.security`
  - `pragmagraph.service`
  - `pragmagraph.workspace`
- immutable DTOs for source refs, graph nodes, graph edges, snapshots, query
  hits, omitted diagnostics, path results, and health summaries
- deterministic JSON snapshot load/save helpers
- a local indexer for directories, files, Markdown headings and references,
  Python AST modules/classes/functions/methods/imports/calls/inheritance,
  lexical TypeScript/JavaScript modules/functions/classes/imports/exports,
  optional precise Tree-sitter-backed TypeScript/JavaScript structure when the
  `precise` extra is installed,
  selected JSON/TOML/YAML config metadata, lexical snippets, and local
  git-history overlays for commits and changed paths
- query, explain, neighborhood, path, reverse-import, reverse-dependency,
  backlink, impact, refresh, health, recent git commits by path, files touched
  by commit, and commits touching a symbol's file over loaded snapshots
- content-hash refresh manifests with parser/version metadata, root metadata,
  per-path reason codes, and deterministic structural delta helpers
- package-owned explicit refresh operations: refresh previews, saved invocation
  profiles, persistent refresh status ledgers, repeatable explicit-run helpers,
  and root-backed service refresh-state reporting
- deterministic structural report helpers with JSON and Markdown output for
  repo summaries, unresolved facts, top nodes, hotspots, structural summaries,
  dependency/config declarations, and agent-oriented follow-up queries
- deterministic DOT and Mermaid export helpers for lightweight graph viewing
  and downstream tooling, with explicit export-schema markers
- deterministic Graphify-shaped JSON import/export helpers for backend
  interchange tests and provider-swap validation, with explicit interop schema
  versioning
- package-owned local query service contracts and a stdio runner for repeated
  snapshot-backed or root-backed sessions, including richer capabilities,
  health, refresh, and git-overlay metadata
- package-owned persistent workspace helpers for one local root: deterministic
  workspace metadata, saved profile/snapshot/manifest/status layout, explicit
  workspace refresh, workspace status inspection, and `serve --workspace`
- package-owned UI boundary contracts in `pragmagraph.ui` for the future
  OpenMinion third-brain workbench: search, result detail, neighborhood, path,
  and provider-status screens without bundling a separate UI runtime into this
  package
- package-owned benchmark helpers plus repo-local regression fixtures for
  readiness review, fixture profiling, refresh benchmarking, and omitted-rate
  tracking
- scope/security policy for gitignore-aware, size-bounded, binary/symlink-safe
  local indexing
- CLI commands for `index`, `refresh`, `query`, `explain`, `report`, `export`,
  `benchmark`, `graphify-export`, `graphify-import`, `neighborhood`, `path`,
  `health`, `git-commits-for-path`, `git-files-for-commit`,
  `git-commits-for-symbol`, `workspace-init`, `workspace-refresh`,
  `workspace-status`, and `serve`
- a semantic smoke entrypoint for install validation
- package-local tests, lint, and release-check workflow
- API compatibility and release docs

## What the package does not provide yet

This package does **not** currently provide:

- SQLite, KuzuDB, Neo4j, hosted, vector, or typed-edge storage
- Graphify runtime API wrapping or Graphify replacement behavior
- file watchers, git hooks, daemons, or scheduled refresh
- MCP, HTTP, WebSocket, or hosted service transports
- OpenMinion runtime provider wiring
- prompt context merging
- the actual operator-facing workbench runtime UI (that belongs to OpenMinion;
  `pragmagraph.ui` only defines the typed package boundary)
- semantic inference from prose or model output
- automatic Sophiagraph memory writes or promotion

Those features belong to follow-on releases or to OpenMinion's provider
adapter layer.

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

## Package-local docs and release

- `docs/README.md` summarizes the package-local docs contract.
- `API_COMPATIBILITY.md` records the supported public import roots and
  top-level export policy.
- `RELEASING.md` records the package-local release and PyPI publish flow.
- `docs/reference/service-mode.md` records the local service request/response
  contract, including parser provenance in capabilities and health payloads.
- `docs/reference/workspace-mode.md` records the persistent local workspace
  contract.
- `docs/reference/refresh-operations.md` records the package-owned explicit
  refresh/profile/status contract.
- `docs/reference/report-mode.md` records the structural report contract.
- `docs/reference/export-mode.md` records the deterministic export contract.
- `docs/reference/graphify-interop.md` records the deterministic Graphify
  interchange contract.
- `docs/reference/benchmarking.md` records the benchmark surface and readiness
  posture.
- `docs/reference/git-history-mode.md` records the local git-overlay contract,
  privacy posture, and CLI shape.
- `docs/reference/ui-contracts.md` records the package-owned UI boundary
  contract.
- `src/pragmagraph/README.md` explains the source-tree module layout and
  public-vs-repo-local boundary.
- `scripts/release_check.py` is the canonical release smoke entrypoint.
- `tests/fixtures/repos/` and `tests/contracts/` hold repo-local regression
  fixtures and OpenMinion contract snapshots; they are validation assets, not
  public package API.

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

See [API_COMPATIBILITY.md](API_COMPATIBILITY.md) for the public import-root
policy, [docs/reference/report-mode.md](docs/reference/report-mode.md) for the
structural report contract, [docs/reference/export-mode.md](docs/reference/export-mode.md)
for deterministic graph exports, [docs/reference/benchmarking.md](docs/reference/benchmarking.md)
for the benchmark/readiness surface, [docs/reference/graphify-interop.md](docs/reference/graphify-interop.md)
for Graphify-shaped JSON interchange, [docs/reference/workspace-mode.md](docs/reference/workspace-mode.md)
for the persistent local workspace contract,
[docs/reference/certification-readiness-matrix.md](docs/reference/certification-readiness-matrix.md)
for package/OpenMinion proof coverage, and [RELEASING.md](RELEASING.md) for
package-local release checks.
