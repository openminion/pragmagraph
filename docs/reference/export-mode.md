# PragmaGraph Export Mode

Status: semantic alpha

## Purpose

Export mode renders a PragmaGraph snapshot into deterministic graph text formats
that operators, agents, docs, and external tooling can consume without adopting a
PragmaGraph storage backend.

The current package-owned formats are:

- Graphviz DOT via `render_dot(snapshot)`
- Mermaid flowchart text via `render_mermaid(snapshot)`
- format-dispatch helper via `render_graph_export(snapshot, format=...)`

## CLI

```bash
pragmagraph export .pragmagraph/snapshot.json --format dot
pragmagraph export .pragmagraph/snapshot.json --format mermaid
```

The CLI writes graph text to stdout. It does not invoke Graphviz, render HTML, or
open a browser.

## Contract

Exports are deterministic for the same snapshot:

1. nodes are ordered by snapshot node ID,
2. edges are ordered by snapshot edge ID,
3. missing-edge endpoints are skipped rather than repaired,
4. node labels include the observed label, kind, and source path when available,
5. edge labels use the observed edge kind.

Export mode does not infer design intent, call relationships beyond indexed
facts, ownership, or recommended architecture changes. Those judgments belong to
the caller or to a separate LLM-owned analysis step.

## Intended Uses

- attach quick visual graph text to CI artifacts,
- paste Mermaid output into Markdown docs or issues,
- feed DOT output to Graphviz in downstream tooling,
- let OpenMinion or another agent runtime summarize a source graph without
  depending on a browser, hosted graph service, or visualization package.
