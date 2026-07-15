# PragmaGraph Code Quality and Hygiene

This is the public contributor version of the package's code-quality rules.

The short version:

1. keep observed-fact contracts typed and reproducible,
2. keep package boundaries honest,
3. keep runtime behavior structural rather than speculative,
4. keep comments minimal,
5. and prove the change with validation.

## 1. Prefer one truthful owner

Use the nearest clear owner:

1. typed records and snapshots in `models/` and `contracts/`
2. query behavior in `query/`
3. storage and snapshot persistence in `storage/`
4. report/export surfaces in their named packages
5. refresh, service, workspace, and operations behavior in their named owners

Avoid:

1. duplicate helpers,
2. repeated magic literals,
3. ad hoc wrappers around canonical package owners.

## 2. Keep runtime behavior structural, not speculative

PragmaGraph owns observed, reproducible facts from source artifacts.

Avoid:

1. LLM-owned judgment in the package core,
2. lossy semantic inference,
3. implicit promotion of observations into non-reproducible claims.

Prefer:

1. typed fields,
2. deterministic snapshots,
3. explicit parser and refresh contracts,
4. clear owner boundaries.

## 3. Keep names and layout honest

Rules:

1. remove stale names instead of letting them linger,
2. keep files in the package area that truthfully owns them,
3. do not grow generic junk-drawer files like `utils.py`.

## 4. Keep public docs portable

Do not add:

1. machine-local absolute paths,
2. private workstation assumptions,
3. internal tracker-state wording as public package documentation.

## 5. Keep changes focused

Good practice:

1. one clear purpose per PR,
2. update tests near the change,
3. avoid unrelated refactors in the same patch.

## 6. Validate before calling work done

Before closing work, run the package gates from `pragmagraph/`:

```bash
make check
```

`make check` runs formatting, Ruff, structural quality ratchets, and the
package tests. The ratchets guard current debt for file/function size,
duplicate private helpers, path and filename drift, broad exception handlers,
bare `# type: ignore`, and hidden sibling-package imports.

If your change affects packaging or public release shape, also run:

```bash
make release-check
```

Use `make lint` or `make test` directly only when you need a narrower loop
while iterating.

## 7. When in doubt, choose clarity over cleverness

The package prefers:

1. explicit owners over convenience,
2. deterministic observed facts over magical ones,
3. maintainable structure over short-term shortcuts.
