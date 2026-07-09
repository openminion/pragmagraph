# Releasing `pragmagraph`

Status: `alpha`
Scope: package-local release contract for the standalone `pragmagraph`
distribution

`pragmagraph` is published under Apache-2.0. This document keeps the
package-local release path explicit so publishing does not depend on host
framework or monorepo context.

## Release Contract

A publishable release must satisfy all of the following:

1. `pyproject.toml` and `src/pragmagraph/__init__.py` agree on the version.
2. `LICENSE` is present and included in built artifacts.
3. `README.md` describes install, quickstart, smoke, name meaning, and
   import-boundary expectations for external consumers.
4. `API_COMPATIBILITY.md` names the stable import roots and deprecation policy.
5. `docs/` remains the canonical package-local docs root.
6. `docs/source-tree-owner-map.md` continues to document the
   source-tree owner map and repo-local validation assets.
7. `pragmagraph.service` and `pragmagraph serve` remain documented when
   present in the public alpha contract.
8. `pragmagraph.ui` remains documented as a typed boundary contract when
   present in the public alpha contract.
9. Package tests pass from the package root.
10. Both wheel and sdist build successfully.
11. A clean install smoke passes from a fresh virtualenv using the built wheel.
12. The package still has no imports from host frameworks such as OpenMinion.
13. Semantic-alpha releases keep graph facts reproducible from local source
   artifacts and do not import OpenMinion.

## Version Bump

Update both locations together:

- `pyproject.toml`
- `src/pragmagraph/__init__.py`

If the release changes the external consumer contract, also update:

- `README.md`
- `API_COMPATIBILITY.md`
- `docs/README.md`
- `docs/source-tree-owner-map.md`
- `docs/report-mode.md`
- `docs/export-mode.md`
- `docs/graphify-interop.md`
- `docs/benchmarking.md`
- `docs/service-mode.md`
- `docs/ui-contracts.md`

## Build and Validation

Preferred deterministic release check:

```bash
python3.11 scripts/release_check.py
```

The script runs package pytest, wheel+sdist build, `twine check`, and a
fresh-wheel smoke automatically.

Manual equivalent:

```bash
rm -rf build dist src/*.egg-info
python3.11 -m pytest -q
python3.11 -m build
python3.11 -m twine check dist/*
```

Fresh-install smoke:

```bash
TMP_VENV="$(mktemp -d)/pragmagraph-venv"
python3.11 -m venv "$TMP_VENV"
"$TMP_VENV/bin/pip" install dist/pragmagraph-*.whl
"$TMP_VENV/bin/pragmagraph-smoke" --json
```

Expected smoke result:

- JSON output with `package` equal to `pragmagraph`
- `semantic_contract` equal to `true`
- stable import roots listed

If the release includes the service surface, the fresh-wheel smoke must also be
able to import `pragmagraph.service`.

If the release includes the package-owned UI boundary contract, the fresh-wheel
smoke must also be able to import `pragmagraph.ui`.

## Publish Sequence

This package now owns the same GitHub Actions release shape used by the sibling
packages:

1. RC tags such as `v0.0.5rc1` publish to TestPyPI.
2. Manual `workflow_dispatch` with `target=testpypi` publishes the final
   version to TestPyPI from the final release branch.
3. Final tags such as `v0.0.5` publish to production PyPI.
4. GitHub Releases should use the bare version title such as `0.0.5`.

The deterministic local gate still starts with the package-owned smoke script:

```bash
rm -rf build dist src/*.egg-info
python3.11 scripts/release_check.py
```

After local proof is green, use the repo-family release flow documented in
`docs/reference/package-release-process.md`:

1. bump RC version surfaces,
2. run local proof,
3. push the RC branch and RC tag,
4. verify the hosted TestPyPI RC publish,
5. bump to the final version on a final release branch,
6. manually dispatch the final branch to TestPyPI,
7. push the final tag to production PyPI,
8. create the GitHub Release,
9. merge the final release branch into the public default branch,
10. back-merge the public default branch into the release source branch when
    those branches differ,
11. remove temporary release branches after the merge.

After a production upload, the project name `pragmagraph` is owned by the PyPI
account or organization used for the release.

## Notes

1. Repository and PyPI project URLs are package metadata once the GitHub
   repository is created.
2. `pragmagraph` may be published independently; host frameworks consume it as
   an observed-fact graph substrate.
3. Generated caches and `*.egg-info` directories are build artifacts and should
   not be kept as source-of-truth package content.
4. For fast local verification,
   `python3.11 scripts/release_check.py --skip-twine` is acceptable when
   `twine` is not available, but full release sign-off should run the default
   command.
