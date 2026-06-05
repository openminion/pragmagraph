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
2. snapshot serialization,
3. query execution,
4. report generation,
5. DOT export,
6. Mermaid export,
7. Graphify-shaped JSON export.

The report also records total node count, edge count, and snapshot size in
bytes.

## Fixture policy

`tests/fixtures/repos/medium_repo/` is the current repo-local regression
fixture for benchmark and readiness checks. It is intentionally larger and more
connected than `tiny_repo` and `mixed_repo`: nested Python modules, multiple
docs, and multiple config files.

## Readiness note

The benchmark surface is for regression detection and package-level readiness
review. It does not promise a fixed SLA, hosted-service throughput, daemon
behavior, or OpenMinion runtime latency under live prompt assembly.
