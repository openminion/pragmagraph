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
5. Package tests pass from the package root.
6. Both wheel and sdist build successfully.
7. A clean install smoke passes from a fresh virtualenv using the built wheel.
8. The package still has no imports from host frameworks such as OpenMinion.
9. Semantic-alpha releases keep graph facts reproducible from local source
   artifacts and do not import OpenMinion.

## Version Bump

Update both locations together:

- `pyproject.toml`
- `src/pragmagraph/__init__.py`

If the release changes the external consumer contract, also update:

- `README.md`
- `API_COMPATIBILITY.md`

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

## Publish Sequence

Publishing mirrors the Sophiagraph package flow: the top-level release workflow
delegates publishing to `./.github/workflows/_reusable/release.yml`, which uses
`pypa/gh-action-pypi-publish@release/v1`. Local Twine is used only for
`twine check` inside `scripts/release_check.py`; do not use local Twine upload
for normal releases.

After validation is green:

1. Push the release tag, for example `v0.0.1`.
2. Run the GitHub Actions workflow `Release Pipeline` from the PragmaGraph
   repository.
3. Set `release_tag` to the tag being released.
4. Enable `publish_pypi` for the production PyPI release.

The workflow expects the GitHub secret `pypi-token`, matching the Sophiagraph
release workflow secret name.

Manual build/check remains available for local validation:

```bash
rm -rf build dist src/*.egg-info
python3.11 scripts/release_check.py
```

After a production upload, the project name `pragmagraph` is owned by the
publishing PyPI account/organization for future releases.

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
