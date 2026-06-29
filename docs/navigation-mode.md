# Navigation Mode

Status: semantic alpha
Scope: package-local compact repository maps and handoff views

PragmaGraph ships a compact navigation surface for quickly inspecting an
observed graph snapshot without opening a full workbench UI.

## Public root

- `pragmagraph.navigation`

## What it provides

- `build_repo_map(snapshot, top_n=...)` for deterministic sectioned summaries
- `render_markdown_repo_map(repo_map)` for human-readable repository maps
- `render_compact_handoff(snapshot, top_n=...)` for short agent handoff notes
- `RepoMap` and `RepoMapSection` DTOs with stable `to_dict()` output

## CLI entrypoints

Render Markdown:

```bash
pragmagraph repo-map snapshot.json
```

Render JSON:

```bash
pragmagraph repo-map snapshot.json --json
```

Render the shorter handoff view:

```bash
pragmagraph repo-map snapshot.json --handoff
```

## Boundary

Navigation mode summarizes facts already present in the snapshot:

1. node and edge counts,
2. parser set,
3. top directories and files,
4. symbol and doc-section pointers,
5. recent git commit facts when the snapshot contains a git overlay,
6. omitted diagnostic reason counts.

It does not infer owner intent, risk, architectural quality, or semantic
meaning. Those judgments belong outside PragmaGraph.
