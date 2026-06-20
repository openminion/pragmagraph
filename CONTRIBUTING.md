# Contributing to PragmaGraph

Thanks for contributing.

## Before coding

Read these docs before coding:

1. [README.md](./README.md)
2. [API_COMPATIBILITY.md](./API_COMPATIBILITY.md)
3. [docs/README.md](./docs/README.md)
4. [docs/source-tree-owner-map.md](./docs/source-tree-owner-map.md)
5. [RELEASING.md](./RELEASING.md) when the work affects packaging or release
   behavior

Treat the package README and API compatibility policy as the stable public
contract, and use the docs index plus owner map to understand which surfaces
the package does and does not own.

## Quick start

1. Fork and create a branch.
2. Make focused changes.
3. Add or update tests.
4. Open a PR with a clear summary.

## Repository layout

```text
pragmagraph/
├── src/pragmagraph/            # public package shipped on PyPI
│   ├── contracts/  models/  adapters/  query/
│   ├── storage/  report/  export/  graphify/
│   ├── refresh/  service/  security/  ui/
│   ├── bench/  parsers/  workspace/
│   └── operations.py
├── tests/                      # package tests and contract fixtures
│   ├── fixtures/repos/         # regression fixture repositories
│   └── contracts/              # OpenMinion-facing contract fixtures
├── docs/                       # public package-local docs
├── pyproject.toml
└── scripts/release_check.py    # package release smoke
```

The public wheel is everything under `src/pragmagraph/`. Fixture repositories,
contract snapshots, package docs, and release tooling support the package but
do not enlarge the documented runtime API beyond `README.md`,
`API_COMPATIBILITY.md`, and `docs/`.

## Setup

Requires Python 3.11+.

```bash
# 1. Clone and enter the repo
git clone https://github.com/openminion/pragmagraph.git pragmagraph
cd pragmagraph

# 2. Create and activate a virtualenv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode with dev extras
make dev-install
```

Install the optional precise parser family when you need Tree-sitter-backed
TypeScript/JavaScript structure:

```bash
python3.11 -m pip install -e ".[precise]"
```

## Running tests

```bash
# Full package test suite
make test

# Full local quality gate
make check

# Release/install smoke
make release-check
```

If you need a narrower loop while iterating, run `python3.11 -m pytest -q
tests/<target>` inside the activated virtualenv.

## Running lint and formatting

```bash
# Lint only
make lint

# Check formatting without rewriting files
make format-check

# Apply formatting and autofixes
make fix
```

## Development basics

1. Follow the existing typed, deterministic package style.
2. Keep PRs small and reviewable.
3. Include validation commands and results in the PR description.
4. Prefer a short GitHub-native PR title plus a flat bullet summary of what the
   commit set landed.
5. Keep PR descriptions easy to scan and easy to copy:
   1. short title
   2. bullet summary of changes
   3. validation commands/results
6. PragmaGraph owns observed, reproducible facts. Do not add LLM-owned,
   judgmental, or lossy semantic behavior to the package core.
7. Keep package/runtime boundaries explicit. Public package docs should stay
   public-facing and portable.
8. Add or update tests for any behavior change. Tests live under `tests/`.
9. Do not turn fixture repos, contract snapshots, or examples into accidental
   public API promises.
10. Do not bundle unrelated refactors into the same PR.

Preferred PR shape:

1. `Title`
   - short and literal, for example `Add explicit refresh operations spine`
2. `Description`
   - `- add ...`
   - `- align ...`
   - `- polish ...`
3. `Validation`
   - `- <command>`
   - `- <command>`

## Submitting a pull request

1. Fork and create a branch from `main`.
2. Make your change; add or update tests; run the relevant local validation.
3. Open a PR with a clear summary. In the description, include:
   - what changed and why,
   - the exact commands you ran for validation,
   - whether the change affects the public standalone package surface,
     optional parser support, or repo-local fixtures/contracts/tooling.
4. Keep PRs small and reviewable.
5. Do not bundle unrelated refactors into the same PR.

## Legal basics (plain English)

1. You keep ownership of your contributions.
2. By submitting a contribution, you license it under the project license
   (Apache-2.0).
3. Apache-2.0 includes a patent license for your contribution, with the
   standard patent-termination condition in the license text.
4. Only submit code or content you have the right to contribute.
5. Do not add third-party code or assets unless their license is compatible
   and clearly documented.
6. Project names and logos are not granted for endorsement use.
7. `pragmagraph` is provided on an "as is" basis under the project license;
   there are no guarantees about performance, reliability, availability, or
   fitness for a particular use case.
8. If you configure third-party services or paid infrastructure while
   developing or testing, you are responsible for any resulting charges.
9. See [LICENSE](./LICENSE) for the full legal terms, disclaimers, and
   limitations of liability.

## Security

If you find a security issue, do not open a public issue with exploit details.
Use the project security reporting process.

## Code of conduct

By participating, you agree to follow [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
