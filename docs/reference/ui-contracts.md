# PragmaGraph UI Contracts

Status: semantic alpha
Scope: typed UI boundary contracts only

`pragmagraph.ui` is the package-owned typed boundary for future operator-facing
third-brain workbench screens.

The important ownership rule is explicit:

1. `pragmagraph` owns typed observed-fact graph contracts and the package-local
   UI boundary surface,
2. `openminion` owns the actual runtime workbench UI and provider-neutral
   operator experience.

## Current contract

- owner import root: `pragmagraph.ui`
- runtime package: `openminion`
- transport kind: `openminion_workbench`
- transport status: `planned_not_implemented`
- current API seam: `openminion.modules.context.knowledge_graphs`

## Screen manifest

The first screen manifest is intentionally small and matches the workbench MVP:

1. search
2. result detail
3. neighborhood
4. path
5. provider status

## Boundary

This package does **not** currently ship a browser app, Textual TUI, REST
server, or MCP UI server. It ships typed UI contracts so package structure
stays aligned with sibling standalone packages and future UI work has one
canonical import root.
