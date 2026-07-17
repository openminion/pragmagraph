# Native SCIP certification fixtures

These fixtures are generated from the tiny source trees in this directory by
official Sourcegraph indexers. Default tests consume the checked-in binary
files and never install or launch an indexer.

Regenerate the Python fixture from `tests/fixtures/scip/python`:

```bash
npx -y @sourcegraph/scip-python@0.6.6 index \
  --project-name=pgpi-python-fixture \
  --project-version=1.0.0 \
  --target-only=src \
  --output=index.scip
python3.11 ../../../../scripts/schema/normalize_fixture.py \
  index.scip \
  --project-root=file:///fixtures/pragmagraph/scip/python
```

Regenerate the TypeScript fixture from `tests/fixtures/scip/typescript`:

```bash
npm install --ignore-scripts
npx -y @sourcegraph/scip-typescript@0.4.0 index --output=index.scip
python3.11 ../../../../scripts/schema/normalize_fixture.py \
  index.scip \
  --project-root=file:///fixtures/pragmagraph/scip/typescript
```

The normalization step changes only `metadata.project_root`. It prevents a
contributor workstation path from entering a public fixture while retaining
the official producer's symbols, occurrences, relationships, and metadata.

The producer packages and the SCIP schema are Apache-2.0. The fixture source
and generated indexes are maintained as PragmaGraph test artifacts under this
repository's Apache-2.0 license.
