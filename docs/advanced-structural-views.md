# Advanced Structural Views

Status: semantic alpha

PragmaGraph includes several derived views over the same observed snapshot.
These views do not infer author intent, code quality, risk, or memory meaning;
they reorganize facts already present in the snapshot so agents and tools can
navigate faster.

## Symbol/reference interchange

Use the interchange view when a consumer needs a stable symbol/reference payload
without depending on every snapshot field.

```bash
PYTHONPATH=src python3.11 -m pragmagraph interchange snapshot.json
```

The payload includes:

1. symbol-like nodes such as Python classes/functions and script exports,
2. structural reference edges such as defines, imports, calls, mentions, and
   document references,
3. deterministic diagnostics with symbol and reference counts.

## Topology

Use topology mode to inspect graph shape: connected components, high-degree
nodes, isolated nodes, and node/edge kind counts.

```bash
PYTHONPATH=src python3.11 -m pragmagraph topology snapshot.json
PYTHONPATH=src python3.11 -m pragmagraph topology snapshot.json --json
```

Topology output is structural only. A high-degree node is reported as a
high-degree node; the package does not label it risky, important, stale, or
suspicious.

## Document graph

Use document-graph mode to inspect document backlinks and unresolved mention
candidates.

```bash
PYTHONPATH=src python3.11 -m pragmagraph doc-graph snapshot.json
PYTHONPATH=src python3.11 -m pragmagraph doc-graph snapshot.json --json
```

Unlinked mention candidates are candidates, not edges. Consumers can use them
for review workflows, but PragmaGraph does not promote them into facts without
an indexer-observed relation.

## Query-plan evidence

Use query-plan mode when a caller needs to explain the shape of a deterministic
query run.

```bash
PYTHONPATH=src python3.11 -m pragmagraph query-plan snapshot.json RuntimeGraph
```

The result records the lexical/structural strategy, candidate count, returned
count, omitted count, truncation status, request limits, and filters supported
by the public query DTO.

## Git lineage

Use git-lineage mode to inspect observed commits for one path, including git
rename metadata when git reports it.

```bash
PYTHONPATH=src python3.11 -m pragmagraph git-lineage snapshot.json src/runtime.py
```

Lineage entries include commit hashes, subjects, epoch-plus-offset timestamps,
changed path, previous path for observed renames, additions, and deletions.
They do not summarize or interpret why a change happened.

## Parser support

Use parser-support mode to check which parser families are built in and which
optional parser families are unavailable in the current environment.

```bash
PYTHONPATH=src python3.11 -m pragmagraph parser-support --json
```

Unavailable optional parsers are explicit diagnostics, not silent omissions.

## Certification pack

Use certification mode to bundle public-readiness facts for a snapshot.

```bash
PYTHONPATH=src python3.11 -m pragmagraph certify snapshot.json
```

The certification pack includes node/edge/omitted counts, parser provenance,
privacy/export posture, topology summary facts, cross-repository resolution
counts when present, and a canonical snapshot hash. It is designed for package
consumers that need a compact proof artifact before exchanging or publishing a
snapshot.

Write a Markdown trust pack alongside the JSON payload:

```bash
PYTHONPATH=src python3.11 -m pragmagraph certify snapshot.json \
  --markdown-out certification.md \
  --json
```
