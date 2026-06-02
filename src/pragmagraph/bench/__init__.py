"""Benchmark helpers for PragmaGraph package surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter_ns
from types import MappingProxyType
from typing import Any, Callable, Mapping, TypeVar

from pragmagraph.adapters import index_path
from pragmagraph.export import render_dot, render_mermaid
from pragmagraph.graphify import to_graphify_payload
from pragmagraph.models import QueryRequest
from pragmagraph.query import query
from pragmagraph.report import build_report
from pragmagraph.storage import stable_dumps

_T = TypeVar("_T")


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True)
class BenchmarkMeasurement:
    """One timed package operation."""

    name: str
    duration_ms: float
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _frozen_mapping(self.details))

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
    snapshot_bytes: int
    node_count: int
    edge_count: int
    measurements: tuple[BenchmarkMeasurement, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "measurements", tuple(self.measurements))

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "namespace": self.namespace,
            "query_text": self.query_text,
            "snapshot_bytes": self.snapshot_bytes,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "measurements": [item.to_dict() for item in self.measurements],
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
) -> BenchmarkReport:
    """Benchmark the main package surfaces over ``root_path``."""
    root = Path(root_path).resolve()
    snapshot, index_measurement = _measure(
        "index",
        lambda: index_path(root, namespace=namespace),
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
    query_result, query_measurement = _measure(
        "query",
        lambda: query(
            snapshot,
            QueryRequest(query=query_text, max_results=max_results),
        ),
        detail_builder=lambda value: {
            "hit_count": len(value.hits),
            "candidate_count": int(value.diagnostics.get("candidate_count", 0)),
        },
    )
    report_result, report_measurement = _measure(
        "report",
        lambda: build_report(snapshot, top_n=top_n),
        detail_builder=lambda value: {
            "top_node_count": len(value.top_nodes),
            "dependency_count": len(value.dependencies),
            "unresolved_count": len(value.unresolved_items),
        },
    )
    dot_text, dot_measurement = _measure(
        "export_dot",
        lambda: render_dot(snapshot),
        detail_builder=lambda value: {"bytes": len(value.encode("utf-8"))},
    )
    mermaid_text, mermaid_measurement = _measure(
        "export_mermaid",
        lambda: render_mermaid(snapshot),
        detail_builder=lambda value: {"bytes": len(value.encode("utf-8"))},
    )
    graphify_payload, graphify_measurement = _measure(
        "graphify_export",
        lambda: to_graphify_payload(snapshot),
        detail_builder=lambda value: {
            "node_count": len(value.get("nodes", ())),
            "edge_count": len(value.get("edges", ())),
        },
    )

    _ = query_result, report_result, dot_text, mermaid_text, graphify_payload
    return BenchmarkReport(
        root_path=str(root),
        namespace=snapshot.namespace,
        query_text=query_text,
        snapshot_bytes=len(snapshot_json.encode("utf-8")),
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        measurements=(
            index_measurement,
            snapshot_measurement,
            query_measurement,
            report_measurement,
            dot_measurement,
            mermaid_measurement,
            graphify_measurement,
        ),
    )


def render_markdown_benchmark(report: BenchmarkReport) -> str:
    """Render ``report`` as deterministic Markdown."""
    lines = [
        "# PragmaGraph Benchmark Report",
        "",
        f"- Root: `{report.root_path}`",
        f"- Namespace: `{report.namespace}`",
        f"- Query: `{report.query_text}`",
        f"- Nodes: `{report.node_count}`",
        f"- Edges: `{report.edge_count}`",
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


__all__ = [
    "BenchmarkMeasurement",
    "BenchmarkReport",
    "benchmark_root",
    "render_markdown_benchmark",
]
