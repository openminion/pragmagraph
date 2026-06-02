# PragmaGraph Structural Report Mode

Last updated: 2026-06-01
Status: Active

## Purpose

Document the package-owned structural report surface exposed through
`pragmagraph.report` and `python -m pragmagraph report`.

## Scope

This doc covers:

1. the deterministic JSON and Markdown report contract,
2. the intended use of report output by operators and agent runtimes,
3. the structural boundaries that keep report mode inside PragmaGraph's
   observed-fact remit.

## Non-goals

This doc does not define:

1. hosted dashboards,
2. Graphify import/export,
3. LLM summarization of architecture intent,
4. OpenMinion provider behavior.

## Report contents

The current report surface includes:

1. snapshot summary counts,
2. node-kind counts,
3. edge-kind counts,
4. omitted-reason counts,
5. top nodes by structural degree,
6. declared dependencies extracted from config files,
7. unresolved items derived from omitted diagnostics,
8. deterministic suggested follow-up queries for agents.

## JSON contract

`build_report(snapshot)` returns a `GraphReport` with these sections:

1. `summary`
2. `top_nodes`
3. `orphan_nodes`
4. `unresolved_items`
5. `dependencies`
6. `suggested_queries`

All report DTOs expose `to_dict()` and remain deterministic for the same
snapshot input.

## Markdown contract

`render_markdown_report(report)` renders:

1. a report title,
2. summary bullets,
3. node/edge/omitted count sections,
4. top-node section,
5. dependency section,
6. unresolved-item section,
7. suggested-query section.

The Markdown is structural and cited. It does not explain architectural intent
or infer meanings beyond what the indexer already observed.

## CLI

Markdown output:

```bash
pragmagraph report .pragmagraph/snapshot.json
```

JSON output:

```bash
pragmagraph report .pragmagraph/snapshot.json --json
```

## Anti-LLM boundary

Report mode stays inside the third-brain contract:

1. every fact comes from the snapshot,
2. unresolved items come from typed omitted diagnostics,
3. dependency rows come from indexed config facts,
4. suggested queries are deterministic templates, not generated prose,
5. no report section writes Sophiagraph memory or claims design judgment.
