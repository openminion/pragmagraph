"""Local visual preview helpers backed by GraphFakos."""

from __future__ import annotations

from pathlib import Path
import webbrowser

from graphfakos.server import (
    LocalViewerHttpServer as LocalVisualHttpServer,
    LocalViewerServerResult as LocalVisualServerResult,
    make_local_viewer_server,
    serve_local_viewer,
)
from graphfakos.static import render_static_html

from .graphfakos_adapter import PragmaGraphViewerProvider
from .preview_support import (
    graphfakos_request,
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
    snapshot = snapshot_for_request(request)
    provider = PragmaGraphViewerProvider(snapshot)
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
