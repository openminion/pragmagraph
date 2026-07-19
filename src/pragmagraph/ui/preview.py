"""Local visual preview helpers backed by GraphFakos."""

from __future__ import annotations

from graphfakos import GraphPreviewOutputPaths, write_provider_preview_outputs
from graphfakos.server import (
    LocalViewerHttpServer as LocalVisualHttpServer,
    LocalViewerServerResult as LocalVisualServerResult,
    make_local_viewer_server,
    serve_local_viewer,
)
from graphfakos.static import render_static_html

from .graphfakos_adapter import PragmaGraphViewerProvider
from .preview_inputs import (
    graphfakos_request,
    project_health_context_for_request,
    render_server_preview_path,
    snapshot_for_request,
)
from .preview_types import (
    PreviewScreen,
    UiPreviewRender,
    UiPreviewRequest,
    UiPreviewResult,
)


def write_ui_preview(request: UiPreviewRequest) -> UiPreviewResult:
    """Write one local visual UI preview to an HTML file."""
    snapshot = snapshot_for_request(request)
    provider = PragmaGraphViewerProvider(
        snapshot,
        project_health_context=project_health_context_for_request(request),
    )
    graph_request = graphfakos_request(request)
    payload = write_provider_preview_outputs(
        provider,
        graph_request,
        GraphPreviewOutputPaths(
            html_path=request.output_path,
            artifact_path=request.artifact_path,
            embed_path=request.embed_path,
            report_path=request.report_path,
            markdown_report_path=request.markdown_report_path,
        ),
        open_browser=request.open_browser,
    )
    return UiPreviewResult(
        output_path=str(payload["output_path"]),
        screen=request.screen,
        workspace=request.workspace,
        snapshot=request.snapshot,
        node_count=int(payload["node_count"]),
        edge_count=int(payload["edge_count"]),
        provider_id=str(payload["provider_id"]),
        route=str(payload["route"]),
        artifact=payload.get("artifact"),
        embed=payload.get("embed"),
        report=payload.get("report"),
        markdown_report=payload.get("markdown_report"),
        opened=bool(payload["opened"]),
    )


def render_ui_preview(request: UiPreviewRequest) -> UiPreviewRender:
    """Render the local visual UI preview for a snapshot, workspace, or demo graph."""
    snapshot = snapshot_for_request(request)
    provider = PragmaGraphViewerProvider(
        snapshot,
        project_health_context=project_health_context_for_request(request),
    )
    graph_request = graphfakos_request(request)
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
        render_path=lambda path, query: render_server_preview_path(
            request, path, query
        ),
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
        render_path=lambda path, query: render_server_preview_path(
            request, path, query
        ),
        default_path=f"/{request.screen}",
        host=host,
        port=port,
        open_browser=request.open_browser,
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
