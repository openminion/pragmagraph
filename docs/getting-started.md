# PragmaGraph Getting Started

Status: active
Last updated: 2026-06-20

Purpose: give contributors and automation authors a package-local bootstrap
and execution summary for work inside the `pragmagraph` repo.

## Fast bootstrap

```bash
cd pragmagraph
python3.11 -m venv .venv
source .venv/bin/activate
make dev-install
```

If you need the optional precise parser surface, also install:

```bash
python3.11 -m pip install -e ".[precise]"
```

## Read first

Before substantial code changes, read:

1. [`engineering-patterns.md`](engineering-patterns.md)
2. [`code-quality-enforcement.md`](code-quality-enforcement.md)
3. [`testing-and-validation.md`](testing-and-validation.md)
4. [`source-tree-owner-map.md`](source-tree-owner-map.md)
5. [`workspace-mode.md`](workspace-mode.md) when the work touches persistent
   local workspace behavior

## Normal execution loop

1. Pick one focused change.
2. Implement code and docs together when the public surface changes.
3. Add or update tests for the behavior you changed.
4. Run focused validation while iterating.
5. Run `make check` before calling the work ready.
6. Record validation commands in the PR description.

## Common local checks

Create a snapshot:

```bash
pragmagraph index . --out snapshot.json --json
```

Inspect compact navigation:

```bash
pragmagraph repo-map snapshot.json --handoff
```

Inspect explicit refresh status:

```bash
pragmagraph refresh-status status.json --json
```

## Pull request shape

Preferred PR shape:

1. short, GitHub-native title,
2. flat bullet summary of what changed,
3. short validation block with exact commands.

## Boundary reminder

1. `README.md` is the package contract and install surface.
2. `API_COMPATIBILITY.md` is the public import/export promise.
3. `docs/` is the package-local public docs layer.
4. `tests/` and `scripts/` are important, but they are not public library API.
