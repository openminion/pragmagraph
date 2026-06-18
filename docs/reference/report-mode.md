# PragmaGraph Structural Report Mode

Status: semantic alpha
Scope: deterministic structural report and Markdown rendering contract

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
2. Graphify runtime behavior,
3. LLM summarization of architecture intent,
4. OpenMinion provider behavior.

## Report contents

The current report surface includes:

1. snapshot summary counts,
2. node-kind counts,
3. edge-kind counts,
4. omitted-reason counts,
5. top nodes by structural degree,
6. deterministic hotspot rows,
7. orphan-node rows,
8. declared dependencies and config posture extracted from config files,
9. unresolved items derived from omitted diagnostics,
10. recent git overlay commit rows when git facts are present,
11. structural summary sections,
12. deterministic suggested follow-up queries for agents.

## JSON contract

`build_report(snapshot)` returns a `GraphReport` with these sections:

1. `summary`
2. `top_nodes`
3. `orphan_nodes`
4. `unresolved_items`
5. `dependencies`
6. `hotspots`
7. `git_commits`
8. `structural_summary`
9. `suggested_queries`

All report DTOs expose `to_dict()` and remain deterministic for the same
snapshot input.

## Markdown contract

`render_markdown_report(report)` renders:

1. a report title,
2. summary bullets,
3. node/edge/omitted count sections,
4. dependency and config counts,
5. top-node section,
6. hotspot section,
7. dependency section,
8. unresolved-item section,
9. git-overlay section,
10. structural-summary section,
11. suggested-query section.

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
5. hotspot and structural-summary sections remain structural-only,
6. git commit subjects remain raw metadata rather than semantic summaries,
7. no report section writes Sophiagraph memory or claims design judgment.
