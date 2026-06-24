"""Local visual preview helpers backed by GraphFakos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import webbrowser

from graphfakos import GraphFakosRequest
from graphfakos.server import (
    LocalViewerHttpServer as LocalVisualHttpServer,
    LocalViewerServerResult as LocalVisualServerResult,
    make_local_viewer_server,
    serve_local_viewer,
)
from graphfakos.static import (
    render_static_html,
)
from graphfakos.ui import render_provider_path

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.storage import load_snapshot
from pragmagraph.workspace import load_workspace_metadata

from .graphfakos_adapter import PragmaGraphViewerProvider

PreviewScreen = Literal[
    "search",
    "result_detail",
    "neighborhood",
    "path",
    "provider_status",
]


@dataclass(frozen=True, slots=True)
class UiPreviewRequest:
    """Request for rendering or serving the local PragmaGraph visual UI."""

    screen: PreviewScreen = "search"
    workspace: str | None = None
    snapshot: str | None = None
    output_path: str = "pragmagraph-ui-preview.html"
    query: str = "RuntimeGraph"
    node_id: str | None = None
    source_id: str | None = None
    target_id: str | None = None
    open_browser: bool = False


@dataclass(frozen=True, slots=True)
class UiPreviewResult:
    """File-render result for the local visual preview."""

    output_path: str
    screen: str
    workspace: str | None
    snapshot: str | None
    node_count: int
    edge_count: int
    opened: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": self.output_path,
            "screen": self.screen,
            "workspace": self.workspace,
            "snapshot": self.snapshot,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "opened": self.opened,
        }


@dataclass(frozen=True, slots=True)
class UiPreviewRender:
    """HTML render result for the local visual preview."""

    html: str
    screen: str
    workspace: str | None
    snapshot: str | None
    node_count: int
    edge_count: int


def write_ui_preview(request: UiPreviewRequest) -> UiPreviewResult:
    """Write one local visual UI preview to an HTML file."""
    rendered = render_ui_preview(request)
    output_path = Path(request.output_path).expanduser().resolve(strict=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.html, encoding="utf-8")
    opened = False
    if request.open_browser:
        opened = webbrowser.open(output_path.as_uri())
    return UiPreviewResult(
        output_path=str(output_path),
        screen=rendered.screen,
        workspace=rendered.workspace,
        snapshot=rendered.snapshot,
        node_count=rendered.node_count,
        edge_count=rendered.edge_count,
        opened=opened,
    )


def render_ui_preview(request: UiPreviewRequest) -> UiPreviewRender:
    """Render the local visual UI preview for a snapshot, workspace, or demo graph."""
    snapshot = _snapshot_for_request(request)
    provider = PragmaGraphViewerProvider(snapshot)
    graph_request = _graphfakos_request(request)
    html = render_static_html(provider, graph_request)
    return UiPreviewRender(
        html=html,
        screen=request.screen,
        workspace=request.workspace,
        snapshot=request.snapshot,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
    )


def make_ui_preview_server(
    request: UiPreviewRequest,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
) -> LocalVisualHttpServer:
    """Create a local visual UI server without starting its event loop."""
    return make_local_viewer_server(
        render_path=lambda path, query: _render_server_path(request, path, query),
        default_path=f"/{request.screen}",
        host=host,
        port=port,
    )


def serve_ui_preview(
    request: UiPreviewRequest,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
) -> LocalVisualServerResult:
    """Serve the local visual UI until interrupted."""
    return serve_local_viewer(
        render_path=lambda path, query: _render_server_path(request, path, query),
        default_path=f"/{request.screen}",
        host=host,
        port=port,
        open_browser=request.open_browser,
    )


def _render_server_path(
    request: UiPreviewRequest,
    path: str,
    query: dict[str, list[str]],
) -> str:
    screen = _screen_from_path(path) or request.screen
    next_request = _request_from_query(request, screen=screen, query=query)
    snapshot = _snapshot_for_request(next_request)
    provider = PragmaGraphViewerProvider(snapshot)
    return render_provider_path(
        provider,
        _graphfakos_request(next_request),
        path,
        query,
    )


def _request_from_query(
    request: UiPreviewRequest,
    *,
    screen: PreviewScreen,
    query: dict[str, list[str]],
) -> UiPreviewRequest:
    return UiPreviewRequest(
        screen=screen,
        workspace=_first_query_value(query, "workspace") or request.workspace,
        snapshot=_first_query_value(query, "snapshot") or request.snapshot,
        output_path=request.output_path,
        query=_first_query_value(query, "query") or request.query,
        node_id=_first_query_value(query, "node_id") or request.node_id,
        source_id=_first_query_value(query, "source_id") or request.source_id,
        target_id=_first_query_value(query, "target_id") or request.target_id,
        open_browser=False,
    )


def _first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values and values[0] else None


def _screen_from_path(path: str) -> PreviewScreen | None:
    value = path.strip("/") or "search"
    aliases = {
        "": "search",
        "explore": "search",
        "result": "result_detail",
        "providers": "provider_status",
        "status": "provider_status",
    }
    value = aliases.get(value, value)
    if value in {
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
    }:
        return value  # type: ignore[return-value]
    return None


def _graphfakos_request(request: UiPreviewRequest) -> GraphFakosRequest:
    screen_map = {
        "search": "explore",
        "result_detail": "explore",
        "neighborhood": "neighborhood",
        "path": "path",
        "provider_status": "provider_status",
    }
    return GraphFakosRequest(
        screen=screen_map[request.screen],  # type: ignore[arg-type]
        query=request.query,
        focus_node_id=request.node_id,
        source_node_id=request.source_id,
        target_node_id=request.target_id,
        limit=25,
    )


def _snapshot_for_request(request: UiPreviewRequest) -> GraphSnapshot:
    if request.workspace:
        metadata = load_workspace_metadata(request.workspace)
        return load_snapshot(metadata.paths.snapshot_path)
    if request.snapshot:
        return load_snapshot(request.snapshot)
    return _demo_snapshot()


def _demo_snapshot() -> GraphSnapshot:
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
    "PreviewScreen",
    "UiPreviewRender",
    "UiPreviewRequest",
    "UiPreviewResult",
    "make_ui_preview_server",
    "render_ui_preview",
    "serve_ui_preview",
    "write_ui_preview",
]
