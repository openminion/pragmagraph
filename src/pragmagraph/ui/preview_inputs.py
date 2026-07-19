"""Snapshot, request, and GraphFakos helpers for local UI preview flows."""

from __future__ import annotations

from pathlib import Path

from graphfakos import GraphFakosRequest
from graphfakos.ui import render_provider_path

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.storage import load_snapshot
from pragmagraph.storage.backends import SQLiteGraphStore
from pragmagraph.workspace import load_workspace_metadata, load_workspace_status

from .graphfakos_adapter import PragmaGraphViewerProvider
from .preview_types import PreviewScreen, UiPreviewRequest


def render_server_preview_path(
    request: UiPreviewRequest,
    path: str,
    query: dict[str, list[str]],
) -> str:
    screen = screen_from_path(path) or request.screen
    next_request = request_from_query(request, screen=screen, query=query)
    snapshot = snapshot_for_request(next_request)
    provider = PragmaGraphViewerProvider(
        snapshot,
        project_health_context=project_health_context_for_request(next_request),
    )
    return render_provider_path(
        provider,
        graphfakos_request(next_request),
        path,
        query,
    )


def request_from_query(
    request: UiPreviewRequest,
    *,
    screen: PreviewScreen,
    query: dict[str, list[str]],
) -> UiPreviewRequest:
    return UiPreviewRequest(
        screen=screen,
        workspace=first_query_value(query, "workspace") or request.workspace,
        snapshot=first_query_value(query, "snapshot") or request.snapshot,
        output_path=request.output_path,
        artifact_path=request.artifact_path,
        embed_path=request.embed_path,
        report_path=request.report_path,
        markdown_report_path=request.markdown_report_path,
        store_path=request.store_path,
        query=first_query_value(query, "query") or request.query,
        node_id=first_query_value(query, "node_id") or request.node_id,
        source_id=first_query_value(query, "source_id") or request.source_id,
        target_id=first_query_value(query, "target_id") or request.target_id,
        open_browser=False,
    )


def first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values and values[0] else None


def screen_from_path(path: str) -> PreviewScreen | None:
    value = path.strip("/") or "search"
    aliases = {
        "": "search",
        "explore": "search",
        "result": "result_detail",
        "providers": "provider_status",
        "status": "provider_status",
        "health": "project_health",
        "project-health": "project_health",
    }
    value = aliases.get(value, value)
    if value in {
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
        "project_health",
    }:
        return value  # type: ignore[return-value]
    return None


def graphfakos_request(request: UiPreviewRequest) -> GraphFakosRequest:
    screen_map = {
        "search": "explore",
        "result_detail": "explore",
        "neighborhood": "neighborhood",
        "path": "path",
        "provider_status": "provider_status",
        "project_health": "provider_status",
    }
    return GraphFakosRequest(
        screen=screen_map[request.screen],  # type: ignore[arg-type]
        query=request.query,
        focus_node_id=request.node_id,
        source_node_id=request.source_id,
        target_node_id=request.target_id,
        limit=25,
    )


def snapshot_for_request(request: UiPreviewRequest) -> GraphSnapshot:
    if request.workspace:
        metadata = load_workspace_metadata(request.workspace)
        return load_snapshot(metadata.paths.snapshot_path)
    if request.snapshot:
        return load_snapshot(request.snapshot)
    return demo_snapshot()


def project_health_context_for_request(
    request: UiPreviewRequest,
) -> dict[str, object] | None:
    """Return optional workspace/store facts for the project-health UI payload."""
    context: dict[str, object] = {}
    if request.workspace:
        status = load_workspace_status(request.workspace)
        context["workspace_status"] = status.to_dict()
        if status.refresh_status is not None:
            refresh_status = status.refresh_status
            context["refresh_status"] = {
                "status": refresh_status.status,
                "last_attempt_at": refresh_status.last_attempt_at,
                "last_success_at": refresh_status.last_success_at,
                "last_failure_at": refresh_status.last_failure_at,
                "changed_path_count": refresh_status.changed_path_count,
                "removed_path_count": refresh_status.removed_path_count,
                "added_node_count": refresh_status.added_node_count,
                "removed_node_count": refresh_status.removed_node_count,
                "added_edge_count": refresh_status.added_edge_count,
                "removed_edge_count": refresh_status.removed_edge_count,
                "added_omitted_count": refresh_status.added_omitted_count,
                "removed_omitted_count": refresh_status.removed_omitted_count,
                "manifest_entry_count": refresh_status.manifest_entry_count,
            }
    if request.store_path:
        store_available = Path(request.store_path).exists()
        context["store_status"] = {
            "path": request.store_path,
            "available": store_available,
        }
        if store_available:
            store = SQLiteGraphStore(request.store_path)
            context["store_status"] = {
                "path": request.store_path,
                "available": True,
                "capabilities": store.capabilities().to_dict(),
                "health": store.health().to_dict(),
            }
    return context or None


def demo_snapshot() -> GraphSnapshot:
    nodes = (
        GraphNode(
            id="file:README.md",
            kind="file",
            label="README.md",
            source_ref=SourceRef(path="README.md", line=1),
            text="RuntimeGraph overview and installation notes.",
            metadata={"observed_at": "2026-06-22T00:00:00+00:00"},
        ),
        GraphNode(
            id="module:src/runtime_graph.py",
            kind="python_module",
            label="runtime_graph",
            source_ref=SourceRef(path="src/runtime_graph.py", line=1),
            text="Builds observed graph snapshots for local projects.",
            metadata={"freshness": "fresh"},
        ),
        GraphNode(
            id="symbol:build_runtime_graph",
            kind="python_function",
            label="build_runtime_graph",
            source_ref=SourceRef(path="src/runtime_graph.py", line=12),
            text="Creates a deterministic PragmaGraph snapshot.",
            metadata={"signature": "build_runtime_graph(root)"},
        ),
        GraphNode(
            id="dependency:tree-sitter",
            kind="dependency",
            label="tree-sitter",
            source_ref=SourceRef(path="pyproject.toml", section="dependencies"),
            text="Optional precise parser dependency.",
        ),
    )
    edges = (
        GraphEdge(
            id="edge:readme-docs-module",
            kind="documents",
            source_id="file:README.md",
            target_id="module:src/runtime_graph.py",
        ),
        GraphEdge(
            id="edge:module-defines-symbol",
            kind="defines",
            source_id="module:src/runtime_graph.py",
            target_id="symbol:build_runtime_graph",
        ),
        GraphEdge(
            id="edge:module-uses-parser",
            kind="uses_optional_dependency",
            source_id="module:src/runtime_graph.py",
            target_id="dependency:tree-sitter",
        ),
    )
    return GraphSnapshot(
        namespace="demo",
        root_path="demo/pragmagraph-workspace",
        nodes=nodes,
        edges=edges,
        stats={"parser_set": ("python_ast", "markdown", "config")},
        created_at="2026-06-22T00:00:00+00:00",
    )


__all__ = [
    "demo_snapshot",
    "first_query_value",
    "graphfakos_request",
    "project_health_context_for_request",
    "render_server_preview_path",
    "request_from_query",
    "screen_from_path",
    "snapshot_for_request",
]
