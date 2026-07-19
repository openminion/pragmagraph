# PragmaGraph UI Contracts

Status: semantic alpha
Scope: typed UI boundary contracts plus package-local visual preview

`pragmagraph.ui` is the package-owned typed boundary for future operator-facing
third-brain workbench screens. The package-local preview now renders through
GraphFakos, the shared graph lens package.

The important ownership rule is explicit:

1. `pragmagraph` owns typed observed-fact graph contracts and the package-local
   UI boundary surface,
2. `pragmagraph` owns the GraphFakos adapter used for package smoke, demo, and
   visual navigation of one snapshot/workspace,
3. `graphfakos` owns the reusable viewer shell, graph canvas, local server
   primitive, static HTML export, and shared viewer assertions,
4. `openminion` owns the hosted runtime workbench UI and provider-neutral
   operator experience.

## Current contract

- owner import root: `pragmagraph.ui`
- runtime package: `openminion`
- transport kind: `openminion_workbench`
- transport status: `planned_not_implemented`
- host-runtime seam: OpenMinion's third-brain adapter layer
- reusable local server primitive: `graphfakos.server`
- local visual UI seam: `python3.11 -m pragmagraph ui-preview --serve`
- shared viewer package: `graphfakos`

## Screen manifest

The first screen manifest is intentionally small and matches the workbench MVP:

1. search
2. result detail
3. neighborhood
4. path
5. provider status
6. project health

`project_health` is a PragmaGraph-owned screen id for observed workspace facts
such as node counts, edge counts, omitted reasons, parser set, source path
count, and snapshot creation time. Workspace-backed previews also carry the last
explicit-refresh status and materialized-store availability when those files are
present. The current local preview maps it onto the GraphFakos provider-status
renderer and carries the PragmaGraph-specific health payload inside the graph
artifact.

## Local Visual UI

Use the package-local browser preview to inspect one snapshot or workspace
through the GraphFakos-backed third-brain viewer without starting an OpenMinion
workbench:

```bash
pragmagraph-ui \
  --snapshot ./snapshot.json \
  --screen search \
  --serve \
  --open
```

Workspace-backed preview uses the deterministic workspace layout:

```bash
pragmagraph-ui \
  --workspace ./pragmagraph-workspace \
  --screen project_health \
  --serve
```

The equivalent module form is `python3.11 -m pragmagraph ui-preview`.

## Boundary

This package does **not** currently ship a hosted browser app, Textual TUI,
REST server, or MCP UI server. It ships typed UI contracts, deterministic
PragmaGraph to GraphFakos adapter mapping, compatibility wrappers for the local
visual server primitive, and a package-local visual preview command so package
structure stays aligned with sibling standalone packages and future UI work has
one canonical import root.
