# PragmaGraph Benchmarking

Status: semantic alpha

## Purpose

Benchmarking tracks whether PragmaGraph remains fast enough for local
agent-facing source-graph work as indexing, reporting, export, and interop
surfaces expand.

The package-owned benchmark surface lives under:

- `pragmagraph.bench`
- `benchmark_root(root_path, ...)`
- `render_markdown_benchmark(report)`
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

The report also records:

1. total node count,
2. total edge count,
3. snapshot size in bytes,
4. fixture profile (`small`, `medium`, or `large`),
5. omitted count,
6. omitted rate.

## Fixture policy

`tests/fixtures/repos/medium_repo/` is the current repo-local regression
fixture for benchmark and readiness checks. It is intentionally larger and more
connected than `tiny_repo` and `mixed_repo`: nested Python modules, multiple
docs, multiple config files, and mixed package relationships that exercise
query, report, export, and refresh behavior together.

## Readiness note

The benchmark surface is for regression detection and package-level readiness
review. It does not promise a fixed SLA, hosted-service throughput, daemon
behavior, or OpenMinion runtime latency under live prompt assembly.
