# PragmaGraph Standalone + OpenMinion Certification Readiness Matrix

Status: semantic alpha
Scope: public package proof matrix

## Purpose

Single map of the current public PragmaGraph surface, the standalone package
proof for each lane, and the OpenMinion direct-library proof where one exists.

## Scope

The matrix below lists each shipped PragmaGraph package lane, the exact package
test target that proves the standalone surface works, and the exact OpenMinion
test target that proves the runtime can consume the public package contract.

## Non-goals

This matrix does not cover:

1. hosted graph services,
2. OpenMinion memory behavior,
3. future Graphify interop, hosted visualization, or browser rendering lanes not
   yet implemented.

## Success criteria

Every row that is not `n/a` points to a passing standalone or OpenMinion test
target that exercises only the public package surface.

## Matrix

| Lane | Standalone proof | OpenMinion direct-library proof |
| --- | --- | --- |
| Semantic MVP | `pragmagraph/tests/test_semantic_mvp.py` | `openminion/tests/context/knowledge_graphs/test_pragmagraph_adapter.py` |
| Graphify-parity package expansion | `pragmagraph/tests/test_graphify_parity_expansion.py` | `openminion/tests/context/knowledge_graphs/test_pragmagraph_provider_swap.py` |
| Core features depth lane | `pragmagraph/tests/test_core_features.py` | `n/a` |
| Structural report mode | `pragmagraph/tests/test_report.py` | `n/a` |
| Git-aware structural facts | `pragmagraph/tests/test_git_history.py` | `n/a` |
| Graph text export mode | `pragmagraph/tests/test_export.py` | `n/a` |
| Graphify-shaped JSON interop | `pragmagraph/tests/test_graphify_interop.py` | `n/a` |
| Workspace persistence and `serve --workspace` | `pragmagraph/tests/test_workspace.py`, `pragmagraph/tests/test_service.py::test_service_workspace_startup_uses_persisted_workspace` | `n/a` |
| Benchmark and medium-fixture readiness | `pragmagraph/tests/test_bench.py` | `n/a` |
| Release and smoke contract | `pragmagraph/tests/test_standalone_smoke.py`, `pragmagraph/scripts/release_check.py` | `openminion/tests/runtime/test_bootstrap_memory_retrieve_di.py` |

## Run-the-suite commands

```bash
cd pragmagraph
make check
python3.11 scripts/release_check.py
```

```bash
cd openminion
PYTHONPATH=src:../pragmagraph/src .venv/bin/python3.11 -m pytest -q \
  tests/context/knowledge_graphs/test_pragmagraph_adapter.py \
  tests/context/knowledge_graphs/test_pragmagraph_provider_swap.py \
  tests/runtime/test_bootstrap_memory_retrieve_di.py
.venv/bin/python3.11 -m ruff check .
make lint
```

## Anti-LLM boundary

Every row in this matrix exercises typed structural surfaces only:

1. snapshot DTOs,
2. query/path/neighborhood/report/export/interop/benchmark helpers,
3. refresh and health contracts,
4. OpenMinion adapter behavior over public `pragmagraph` imports.

No row depends on freeform model output or internal OpenMinion-only package
imports.
