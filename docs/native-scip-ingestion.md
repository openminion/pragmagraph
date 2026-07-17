# Native SCIP Ingestion

Status: semantic alpha

PragmaGraph can consume a native SCIP protobuf file produced by an external
indexer. PragmaGraph does not discover, install, download, or launch that
indexer. The package owns deterministic intake, exact observed-fact
normalization, optional composition with a local snapshot, diagnostics, and
read-only report exposure.

## Install

Native protobuf support is optional:

```bash
python3.11 -m pip install "pragmagraph[scip]"
```

Normal imports, local indexing, JSON snapshots, and the SCIP-shaped JSON subset
continue to work without this extra. Native intake then returns the typed
`SCIP_SUPPORT_UNAVAILABLE` error.

## Explicit import

Import one externally generated index:

```bash
pragmagraph precise-import index.scip \
  --root /path/to/repo \
  --namespace my-project \
  --out precise.json \
  --json
```

Compose it with an existing canonical snapshot:

```bash
pragmagraph precise-import index.scip \
  --root /path/to/repo \
  --base local.json \
  --out merged.json \
  --json
```

The base snapshot's namespace is authoritative. Exact duplicate IDs are
deduplicated. Conflicting exact IDs preserve the base fact and emit a
`precise_merge_collision` diagnostic. No fuzzy symbol matching occurs.

## Accepted subset

The initial native importer accepts:

- protocol and producer metadata;
- project root and text/position encoding facts;
- document language and relative path;
- symbol identity, display name, kind, enclosing symbol, and relationships;
- occurrence ranges, symbol roles, syntax kind, and target symbols;
- external symbol identities and package coordinates encoded in SCIP symbols.

Documentation text, document source text, occurrence diagnostics, and fields
outside the pinned schema are not graph facts in this profile. Their grouped
counts remain visible in `ScipLossReport`; malformed facts and unknown wire
bytes are reported separately. This is bounded native SCIP consumption, not a
claim of complete or lossless SCIP compatibility.

SCIP occurrences identify a referenced symbol and source location but do not
reliably identify the containing caller. Native occurrence references are
therefore recorded as file-to-symbol `mentions` edges. PragmaGraph does not
invent caller/callee relations.

## Freshness and atomicity

SCIP metadata carries a project root but no standard source-commit field. The
CLI accepts explicit `--index-commit` and `--workspace-commit` values when the
producer workflow can supply them. Root and commit comparisons each resolve to
`match`, `mismatch`, or `unknown`.

`--strict-freshness` rejects any known mismatch before writing output.
Permissive mode writes the snapshot and records the mismatch in the ingestion
report. Unknown freshness is visible and never treated as a match.

## Privacy and portability

Producer name/version, project root, optional commit identities, and field-loss
counts are stored as observed provenance. The `portable` export profile removes
machine-local project/workspace roots from the native ingestion report without
mutating the canonical snapshot. The importer does not retain producer command
arguments or document source text.

## Service and MCP visibility

Service capabilities expose whether optional native support is available,
whether the loaded snapshot contains a native ingestion report, and the
producer name. Service health includes the full read-only report. MCP clients
can read the same report from:

```text
pragma://precise-ingestion
```

No service or MCP method launches an indexer.

## Certified producers

The offline default test suite includes small indexes generated from
package-owned fixture source with:

- `@sourcegraph/scip-python` `0.6.6`;
- `@sourcegraph/scip-typescript` `0.4.0`.

Regeneration commands, source trees, producer versions, and SHA-256 hashes live
under `tests/fixtures/scip/`. Additional producer families require a pinned,
license-safe fixture and the same exact-fact/loss/determinism proof.
