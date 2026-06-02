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

This semantic alpha provides a small local source-graph MVP:
deterministic DTOs, JSON snapshots, a local code/document indexer, lexical and
structural query helpers, deterministic graph reports, CLI commands, and
fixture handoff artifacts for OpenMinion consumption.

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
  - `pragmagraph.portability`
  - `pragmagraph.parsers`
  - `pragmagraph.export`
  - `pragmagraph.graphify`
  - `pragmagraph.report`
  - `pragmagraph.refresh`
  - `pragmagraph.security`
- immutable DTOs for source refs, graph nodes, graph edges, snapshots, query
  hits, omitted diagnostics, path results, and health summaries
- deterministic JSON snapshot load/save helpers
- a local indexer for directories, files, Markdown headings and references,
  Python AST modules/classes/functions/methods/imports/calls/inheritance, selected
  JSON/TOML/YAML config metadata, and lexical snippets
- query, explain, neighborhood, path, refresh, and health helpers over loaded
  snapshots
- deterministic structural report helpers with JSON and Markdown output for
  repo summaries, unresolved facts, top nodes, dependency declarations, and
  agent-oriented follow-up queries
- deterministic DOT and Mermaid export helpers for lightweight graph viewing
  and downstream tooling
- deterministic Graphify-shaped JSON import/export helpers for backend
  interchange tests and handoff artifacts
- content-hash refresh manifests for deterministic changed/unchanged/removed
  path reporting
- scope/security policy for gitignore-aware, size-bounded, binary/symlink-safe
  local indexing
- CLI commands for `index`, `refresh`, `query`, `explain`, `report`, `export`,
  `graphify-export`, `graphify-import`, `neighborhood`, `path`, and `health`
- a semantic smoke entrypoint for install validation
- package-local tests, lint, and release-check workflow
- API compatibility and release docs

## What the package does not provide yet

This package does **not** currently provide:

- SQLite, KuzuDB, Neo4j, hosted, vector, or typed-edge storage
- Graphify runtime API wrapping or Graphify replacement behavior
- file watchers, git hooks, daemons, or scheduled refresh
- OpenMinion runtime provider wiring
- prompt context merging
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

## CLI Quickstart

Index a local code/docs root into a deterministic JSON snapshot:

```bash
pragmagraph index . --out .pragmagraph/snapshot.json --namespace my-project --json
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

Inspect nearby graph facts:

```bash
pragmagraph neighborhood .pragmagraph/snapshot.json \
  "pragma://my-project/file/src/app.py" --json
```

Check health:

```bash
pragmagraph health .pragmagraph/snapshot.json --json
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

See [API_COMPATIBILITY.md](API_COMPATIBILITY.md) for the public import-root
policy, [docs/report-mode.md](docs/report-mode.md) for the structural report
contract, [docs/export-mode.md](docs/export-mode.md) for deterministic graph
exports, [docs/graphify-interop.md](docs/graphify-interop.md) for Graphify-shaped
JSON interchange, [docs/certification-readiness-matrix.md](docs/certification-readiness-matrix.md)
for package/OpenMinion proof coverage, and [RELEASING.md](RELEASING.md) for
package-local release checks.
