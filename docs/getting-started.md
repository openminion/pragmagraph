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
make hooks-install
```

If you need the optional precise parser surface, also install:

```bash
python3.11 -m pip install -e ".[precise]"
```

If you need to consume externally produced native SCIP files, install:

```bash
python3.11 -m pip install -e ".[scip]"
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

Run the complete local loop:

```bash
pragmagraph quickstart . --json
```

Open the local visual graph after quickstart:

```bash
pragmagraph demo-ui --config .pragmagraph/workspace.toml --serve --open --json
```

Show a compact navigation handoff for the generated snapshot:

```bash
pragmagraph repo-map .pragmagraph/workspace/snapshot.json --handoff
```

Create only a snapshot:

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
2. flat line-item bullets that summarize what changed,
3. plain `Validation` label followed by exact command bullets.

Example:

`Add explicit refresh operations spine`

- add explicit refresh operations
- align standalone package docs
- keep workspace and refresh boundaries clear

Validation
- `make check`

## Commit message shape

Use commit messages in the form:

1. `<type>: <summary>`
2. `<type>(<scope>): <summary>`

Approved current types are:

1. `feat`
2. `fix`
3. `docs`
4. `refactor`
5. `test`
6. `chore`
7. `style`
8. `build`

In `pragmagraph`, scope is optional but encouraged when it improves owner
clarity, for example `ui`, `query`, `refresh`, `report`, `workspace`, `docs`,
or `release`.

Keep the summary specific to the landed change, avoid vague subjects like
`update`, prefer the most specific truthful type, and do not use local
shorthand or planning labels as normal commit types.

## Boundary reminder

1. `README.md` is the package contract and install surface.
2. `API_COMPATIBILITY.md` is the public import/export promise.
3. `docs/` is the package-local public docs layer.
4. `tests/` and `scripts/` are important, but they are not public library API.
