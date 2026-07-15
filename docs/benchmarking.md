# PragmaGraph Benchmarking

Status: semantic alpha
Scope: package-local benchmark helpers and readiness checks

## Purpose

Benchmarking tracks whether PragmaGraph remains fast enough for local
agent-facing source-graph work as indexing, reporting, export, and interop
surfaces expand.

The package-owned benchmark surface lives under:

- `pragmagraph.bench`
- `benchmark_root(root_path, ...)`
- `render_markdown_benchmark(report)`
- `benchmark_generated_scale(node_count)`
- `python -m pragmagraph benchmark ...`

## CLI

```bash
pragmagraph benchmark /path/to/repo --namespace demo --query RuntimeGraph

pragmagraph benchmark /path/to/repo \
  --namespace demo \
  --query RuntimeGraph \
  --json
```

## Measured operations

The current benchmark report times:

1. indexing,
2. unchanged refresh,
3. snapshot serialization,
4. query execution,
5. report generation,
6. DOT export,
7. Mermaid export,
8. Graphify-shaped JSON export.
9. SQLite import and store-native lexical query.

The report also records:

1. total node count,
2. total edge count,
3. snapshot size in bytes,
4. fixture profile (`small`, `medium`, or `large`),
5. omitted count,
6. omitted rate.
7. refresh parse/reuse/hash/overlay work,
8. SQLite query strategy, rows examined, and snapshot-deserialization posture.

## Fixture policy

`tests/fixtures/repos/medium_repo/` is the current repo-local regression
fixture for benchmark and readiness checks. It is intentionally larger and more
connected than `tiny_repo` and `mixed_repo`: nested Python modules, multiple
docs, multiple config files, and mixed package relationships that exercise
query, report, export, and refresh behavior together.

Scale evidence uses generated chain snapshots, so no large payload is checked
in. CI proves deterministic work counts at 1,000 and 10,000 nodes. Release
review may run the same helper at 100,000 nodes. Timing is advisory; canonical
hashes, rows examined/written, snapshot bytes, and deserialization posture are
the regression assertions.

## Readiness note

The benchmark surface is for regression detection and package-level readiness
review. It does not promise a fixed SLA, hosted-service throughput, daemon
behavior, or OpenMinion runtime latency under live prompt assembly.
