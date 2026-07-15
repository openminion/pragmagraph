"""Benchmark helpers for PragmaGraph package surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns
from typing import Any, Callable, Mapping, TypeVar

from pragmagraph._immutables import frozen_mapping
from pragmagraph.adapters import DEFAULT_GIT_IDENTITY_MODE, index_path
from pragmagraph.export import render_dot, render_mermaid
from pragmagraph.graphify import to_graphify_payload
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    QueryRequest,
    SourceRef,
)
from pragmagraph.query import query
from pragmagraph.refresh import refresh_snapshot_incremental
from pragmagraph.report import build_report
from pragmagraph.storage import SQLiteGraphStore, stable_dumps

_T = TypeVar("_T")


@dataclass(frozen=True)
class BenchmarkMeasurement:
    """One timed package operation."""

    name: str
    duration_ms: float
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", frozen_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class BenchmarkReport:
    """Timed benchmark summary over a local source root."""

    root_path: str
    namespace: str
    query_text: str
    fixture_profile: str
    snapshot_bytes: int
    node_count: int
    edge_count: int
    omitted_count: int
    omitted_rate: float
    measurements: tuple[BenchmarkMeasurement, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "measurements", tuple(self.measurements))

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "namespace": self.namespace,
            "query_text": self.query_text,
            "fixture_profile": self.fixture_profile,
            "snapshot_bytes": self.snapshot_bytes,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "omitted_count": self.omitted_count,
            "omitted_rate": self.omitted_rate,
            "measurements": [item.to_dict() for item in self.measurements],
        }


@dataclass(frozen=True)
class GeneratedScaleEvidence:
    """Deterministic non-timing evidence for one generated scale profile."""

    node_count: int
    edge_count: int
    canonical_hash: str
    snapshot_bytes: int
    query_strategy: str
    query_rows_examined: int
    traversal_rows_examined: int
    snapshot_deserialized: bool
    normalized_rows_written: int
    snapshot_payload_bytes_written: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "canonical_hash": self.canonical_hash,
            "snapshot_bytes": self.snapshot_bytes,
            "query_strategy": self.query_strategy,
            "query_rows_examined": self.query_rows_examined,
            "traversal_rows_examined": self.traversal_rows_examined,
            "snapshot_deserialized": self.snapshot_deserialized,
            "normalized_rows_written": self.normalized_rows_written,
            "snapshot_payload_bytes_written": self.snapshot_payload_bytes_written,
        }


def _measure(
    name: str,
    fn: Callable[[], _T],
    *,
    detail_builder: Callable[[_T], Mapping[str, Any]] | None = None,
) -> tuple[_T, BenchmarkMeasurement]:
    started = perf_counter_ns()
    value = fn()
    elapsed_ns = perf_counter_ns() - started
    details = detail_builder(value) if detail_builder else {}
    measurement = BenchmarkMeasurement(
        name=name,
        duration_ms=round(elapsed_ns / 1_000_000.0, 3),
        details=details,
    )
    return value, measurement


def benchmark_root(
    root_path: str | Path,
    *,
    namespace: str = "default",
    query_text: str = "README",
    max_results: int = 10,
    top_n: int = 10,
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
) -> BenchmarkReport:
    """Benchmark the main package surfaces over ``root_path``."""
    root = Path(root_path).resolve()
    snapshot, index_measurement = _measure(
        "index",
        lambda: index_path(
            root,
            namespace=namespace,
            git_identity_mode=git_identity_mode,
        ),
        detail_builder=lambda value: {
            "node_count": len(value.nodes),
            "edge_count": len(value.edges),
            "omitted_count": len(value.omitted),
        },
    )

    snapshot_json, snapshot_measurement = _measure(
        "snapshot_serialize",
        lambda: stable_dumps(snapshot),
        detail_builder=lambda value: {"bytes": len(value.encode("utf-8"))},
    )
    _, query_measurement = _measure(
        "json_query",
        lambda: query(
            snapshot,
            QueryRequest(query=query_text, max_results=max_results),
        ),
        detail_builder=lambda value: {
            "hit_count": len(value.hits),
            "candidate_count": int(value.diagnostics.get("candidate_count", 0)),
        },
    )
    _, report_measurement = _measure(
        "report",
        lambda: build_report(snapshot, top_n=top_n),
        detail_builder=lambda value: {
            "top_node_count": len(value.top_nodes),
            "dependency_count": len(value.dependencies),
            "unresolved_count": len(value.unresolved_items),
        },
    )
    _, dot_measurement = _measure(
        "export_dot",
        lambda: render_dot(snapshot),
        detail_builder=lambda value: {"bytes": len(value.encode("utf-8"))},
    )
    _, mermaid_measurement = _measure(
        "export_mermaid",
        lambda: render_mermaid(snapshot),
        detail_builder=lambda value: {"bytes": len(value.encode("utf-8"))},
    )
    _, graphify_measurement = _measure(
        "graphify_export",
        lambda: to_graphify_payload(snapshot),
        detail_builder=lambda value: {
            "node_count": len(value.get("nodes", ())),
            "edge_count": len(value.get("edges", ())),
        },
    )
    with TemporaryDirectory(prefix="pragmagraph-bench-") as temp_dir:
        store_path = Path(temp_dir) / "graph.sqlite"
        sqlite_store, sqlite_import_measurement = _measure(
            "sqlite_import",
            lambda: SQLiteGraphStore.from_snapshot(snapshot, store_path),
            detail_builder=lambda value: value.manifest().to_dict(),
        )
        _, sqlite_query_measurement = _measure(
            "sqlite_query",
            lambda: sqlite_store.query(
                QueryRequest(query=query_text, max_results=max_results),
            ),
            detail_builder=lambda value: {
                "hit_count": len(value.hits),
                "candidate_count": int(value.diagnostics.get("candidate_count", 0)),
                "fts_available": bool(value.diagnostics.get("fts_available", False)),
                "strategy": str(value.diagnostics.get("strategy", "")),
                "rows_examined": int(value.diagnostics.get("rows_examined", 0)),
                "snapshot_deserialized": bool(
                    value.diagnostics.get("snapshot_deserialized", True)
                ),
            },
        )
    initial_refresh, initial_cache = refresh_snapshot_incremental(
        root,
        namespace=namespace,
        git_identity_mode=git_identity_mode,
    )
    refresh_result, refresh_measurement = _measure(
        "refresh_unchanged",
        lambda: refresh_snapshot_incremental(
            root,
            namespace=namespace,
            previous_manifest=initial_refresh.manifest,
            previous_snapshot=initial_refresh.snapshot,
            previous_cache=initial_cache,
            git_identity_mode=git_identity_mode,
        )[0],
        detail_builder=lambda value: {
            "changed_paths": len(value.changed_paths),
            "unchanged_paths": len(value.unchanged_paths),
            "removed_paths": len(value.removed_paths),
            **value.work.to_dict(),
        },
    )

    return BenchmarkReport(
        root_path=str(root),
        namespace=snapshot.namespace,
        query_text=query_text,
        fixture_profile=_fixture_profile(len(snapshot.nodes)),
        snapshot_bytes=len(snapshot_json.encode("utf-8")),
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        omitted_count=len(snapshot.omitted),
        omitted_rate=round(
            len(snapshot.omitted) / max(1, len(snapshot.nodes) + len(snapshot.edges)),
            6,
        ),
        measurements=(
            index_measurement,
            snapshot_measurement,
            refresh_measurement,
            query_measurement,
            sqlite_import_measurement,
            sqlite_query_measurement,
            report_measurement,
            dot_measurement,
            mermaid_measurement,
            graphify_measurement,
        ),
    )


def build_generated_scale_snapshot(node_count: int) -> GraphSnapshot:
    """Build a compact deterministic chain fixture without checked-in payloads."""
    if node_count < 1:
        raise ValueError("node_count must be positive")
    nodes = tuple(
        GraphNode(
            id=f"pragma://scale/node/{index:06d}",
            kind="symbol",
            label=f"node-{index:06d}",
            source_ref=SourceRef(path=f"src/file-{index // 100:06d}.py"),
            text=f"generated scale node {index:06d}",
            metadata={"ordinal": index, "fixture": "generated"},
        )
        for index in range(node_count)
    )
    edges = tuple(
        GraphEdge(
            id=f"pragma://scale/edge/{index:06d}",
            kind="references",
            source_id=nodes[index].id,
            target_id=nodes[index + 1].id,
        )
        for index in range(node_count - 1)
    )
    return GraphSnapshot(
        namespace="scale",
        root_path="generated://scale",
        nodes=nodes,
        edges=edges,
        stats={"fixture": "generated", "node_count": node_count},
    )


def benchmark_generated_scale(node_count: int) -> GeneratedScaleEvidence:
    """Prove store work counts on a generated profile; timings remain advisory."""
    snapshot = build_generated_scale_snapshot(node_count)
    payload = stable_dumps(snapshot).encode("utf-8")
    with TemporaryDirectory(prefix="pragmagraph-scale-") as temp_dir:
        store = SQLiteGraphStore.from_snapshot(
            snapshot, Path(temp_dir) / "scale.sqlite"
        )
        query_result = store.query(f"node-{node_count - 1:06d}")
        traversal = store.neighborhood(
            snapshot.nodes[0].id,
            depth=2,
            max_results=10,
        )
        update = store.apply_snapshot_delta(snapshot)
    return GeneratedScaleEvidence(
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        canonical_hash=hashlib.sha256(payload).hexdigest(),
        snapshot_bytes=len(payload),
        query_strategy=str(query_result.diagnostics.get("strategy", "")),
        query_rows_examined=int(query_result.diagnostics.get("rows_examined", 0)),
        traversal_rows_examined=int(traversal.diagnostics.get("rows_examined", 0)),
        snapshot_deserialized=bool(
            query_result.diagnostics.get("snapshot_deserialized", True)
        ),
        normalized_rows_written=update.normalized_rows_written,
        snapshot_payload_bytes_written=update.snapshot_payload_bytes_written,
    )


def render_markdown_benchmark(report: BenchmarkReport) -> str:
    """Render ``report`` as deterministic Markdown."""
    lines = [
        "# PragmaGraph Benchmark Report",
        "",
        f"- Root: `{report.root_path}`",
        f"- Namespace: `{report.namespace}`",
        f"- Query: `{report.query_text}`",
        f"- Fixture profile: `{report.fixture_profile}`",
        f"- Nodes: `{report.node_count}`",
        f"- Edges: `{report.edge_count}`",
        f"- Omitted count: `{report.omitted_count}`",
        f"- Omitted rate: `{report.omitted_rate}`",
        f"- Snapshot bytes: `{report.snapshot_bytes}`",
        "",
        "## Measurements",
        "",
    ]
    for measurement in report.measurements:
        lines.append(f"- `{measurement.name}`: `{measurement.duration_ms:.3f} ms`")
        if measurement.details:
            detail_text = ", ".join(
                f"{key}={value}" for key, value in sorted(measurement.details.items())
            )
            lines.append(f"  details: `{detail_text}`")
    return "\n".join(lines) + "\n"


def _fixture_profile(node_count: int) -> str:
    if node_count <= 15:
        return "small"
    if node_count <= 120:
        return "medium"
    return "large"


__all__ = [
    "BenchmarkMeasurement",
    "BenchmarkReport",
    "GeneratedScaleEvidence",
    "benchmark_root",
    "benchmark_generated_scale",
    "build_generated_scale_snapshot",
    "render_markdown_benchmark",
]
