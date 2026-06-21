# PragmaGraph UI Contracts

Status: semantic alpha
Scope: typed UI boundary contracts plus package-local visual preview

`pragmagraph.ui` is the package-owned typed boundary for future operator-facing
third-brain workbench screens.

The important ownership rule is explicit:

1. `pragmagraph` owns typed observed-fact graph contracts and the package-local
   UI boundary surface,
2. `pragmagraph` also owns the local visual preview used for package smoke,
   demo, and visual navigation of one snapshot/workspace,
3. `openminion` owns the hosted runtime workbench UI and provider-neutral
   operator experience.

## Current contract

- owner import root: `pragmagraph.ui`
- runtime package: `openminion`
- transport kind: `openminion_workbench`
- transport status: `planned_not_implemented`
- current API seam: `openminion.modules.context.knowledge_graphs`
- reusable local server primitive: `pragmagraph.ui.local_server`
- local visual UI seam: `python3.11 -m pragmagraph ui-preview --serve`
- shared pattern reference: `docs/reference/package-local-visual-ui-pattern.md`

## Screen manifest

The first screen manifest is intentionally small and matches the workbench MVP:

1. search
2. result detail
3. neighborhood
4. path
5. provider status

## Local Visual UI

Use the package-local browser preview to inspect one snapshot or workspace
without starting an OpenMinion workbench:

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
  --screen provider_status \
  --serve
```

The equivalent module form is `python3.11 -m pragmagraph ui-preview`.

## Boundary

This package does **not** currently ship a hosted browser app, Textual TUI,
REST server, or MCP UI server. It ships typed UI contracts, the same reusable
local visual server primitive used by Sophiagraph, and a package-local visual
preview command so package structure stays aligned with sibling standalone
packages and future UI work has one canonical import root.
