# PragmaGraph Cleanup Workflow

Use this workflow for cleanup, simplification, and maintainability work while
preserving observed-fact and snapshot reproducibility.

## Choose the right scope

1. Use a post-authoring pass for the files changed by one feature.
2. Use a bounded sweep for one package area or explicit file set.
3. Use a broad sweep only when every claimed source, test, or script file will
   receive an explicit review disposition.
4. Keep test cleanup separate when it changes fixture repositories or contract
   snapshots.

Small local cleanup does not need a tracker. Broad cleanup needs a fresh
inventory and a ledger kept outside the committed package surface.

## Freeze the inventory

Before editing, inspect the worktree, preserve unrelated changes, list tracked
files with `git ls-files`, split source/tests/scripts/docs when needed, and
record the exact count.

## Record every disposition

Use one ledger row per claimed file:

`path | area | before LOC | after LOC | disposition | rationale | validation`

Use `trim`, `keep`, `defer-owned:<issue>`, or
`defer-later:<reason>`. Close only when every row has a disposition and the
remaining count is zero.

## Preserve observed facts

Simplify duplicate glue, pass-through wrappers, fake abstractions, repeated
ownership, and unnecessary commentary. Do not replace reproducible facts with
semantic guesses, weaken snapshot determinism, or turn fixture repositories
and contract snapshots into accidental public APIs.

## Validate

Use focused Ruff and pytest while editing. Close with:

```bash
make check
```

Run `make release-check` when packaging, public imports, parser extras, or
installed-wheel behavior changes. Refresh the inventory if the worktree moves
during validation.
