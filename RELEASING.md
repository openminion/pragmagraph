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

Example sequence once validation is green:

```bash
python3.11 -m build
python3.11 -m twine check dist/*
python3.11 -m twine upload dist/*
```

TestPyPI dry run:

```bash
rm -rf build dist src/*.egg-info
python3.11 scripts/release_check.py
python3.11 -m twine upload --repository testpypi dist/*
python3.11 -m venv /tmp/pragmagraph-testpypi-venv
/tmp/pragmagraph-testpypi-venv/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pragmagraph==<version>
/tmp/pragmagraph-testpypi-venv/bin/pragmagraph-smoke --json
```

Production PyPI upload:

```bash
rm -rf build dist src/*.egg-info
python3.11 scripts/release_check.py
python3.11 -m twine upload dist/*
```

Use PyPI API tokens through `TWINE_USERNAME=__token__` and
`TWINE_PASSWORD=...` or a local `.pypirc`; do not commit credentials. After a
production upload, the project name `pragmagraph` is owned by the publishing
PyPI account/organization for future releases.

## Notes

1. This package intentionally omits repository/homepage metadata until the
   canonical public release URLs are locked.
2. `pragmagraph` may be published independently; host frameworks consume it as
   an observed-fact graph substrate.
3. Generated caches and `*.egg-info` directories are build artifacts and should
   not be kept as source-of-truth package content.
4. For fast local verification,
   `python3.11 scripts/release_check.py --skip-twine` is acceptable when
   `twine` is not available, but full release sign-off should run the default
   command.
