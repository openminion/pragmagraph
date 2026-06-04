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
5. `pragmagraph.service` and `pragmagraph serve` remain documented when
   present in the public alpha contract.
6. Package tests pass from the package root.
7. Both wheel and sdist build successfully.
8. A clean install smoke passes from a fresh virtualenv using the built wheel.
9. The package still has no imports from host frameworks such as OpenMinion.
10. Semantic-alpha releases keep graph facts reproducible from local source
   artifacts and do not import OpenMinion.

## Version Bump

Update both locations together:

- `pyproject.toml`
- `src/pragmagraph/__init__.py`

If the release changes the external consumer contract, also update:

- `README.md`
- `API_COMPATIBILITY.md`
- `docs/service-mode.md`

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

## Publish Sequence

This package intentionally mirrors Sophiagraph's package-local setup: the
package directory owns build, check, metadata, and release-smoke validation. It
does not own a package-local GitHub Release workflow.

After validation is green, publish through the same external PyPI release
process used for Sophiagraph, using the artifacts produced by
`scripts/release_check.py`.

```bash
rm -rf build dist src/*.egg-info
python3.11 scripts/release_check.py
```

After a production upload, the project name `pragmagraph` is owned by the PyPI
account/organization used for the release.

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
