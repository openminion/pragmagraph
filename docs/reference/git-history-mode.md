# Git History Mode

Status: semantic alpha
Scope: package-local git overlay and privacy contract

`pragmagraph` can enrich a snapshot with local git-history overlays while
staying inside the observed-fact boundary.

## What the git overlay adds

1. commit nodes with raw commit hash, parent hashes, subject line, and raw
   epoch-plus-offset timestamps,
2. changed-path nodes for repo-relative paths touched by included commits,
3. commit-to-path and commit-to-current-file edges,
4. typed diagnostics when git is unavailable, the root is not a repo, or the
   repository is shallow.

## Boundary rules

1. commit subjects stay raw metadata,
2. no semantic interpretation of author intent, risk, or recommendation,
3. no hosted forge metadata,
4. no automatic memory writes.

## Privacy posture

1. default mode is `name_email_hash`, which keeps author/committer names and a
   stable hash of the email address without exporting the raw email,
2. `full` mode is explicit opt-in and may surface raw email addresses,
3. service capabilities and snapshot stats advertise the active identity mode.

## Determinism rules

1. timestamps are stored as raw git epoch-plus-offset facts,
2. recent-commit ordering sorts by epoch, not localized rendering,
3. the same repo state must produce byte-identical snapshot JSON across
   differing `TZ` environments.

## CLI examples

```bash
pragmagraph index . \
  --out .pragmagraph/snapshot.json \
  --namespace my-project \
  --git-identity-mode name_email_hash \
  --json

pragmagraph git-commits-for-path .pragmagraph/snapshot.json src/app.py --json
pragmagraph git-files-for-commit .pragmagraph/snapshot.json abc123def456 --json
pragmagraph git-commits-for-symbol \
  .pragmagraph/snapshot.json \
  "pragma://my-project/python_class/src/app.py:RuntimeGraph" \
  --json
```
