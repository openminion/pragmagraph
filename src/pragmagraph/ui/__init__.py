"""Typed workbench-boundary contracts for in-package PragmaGraph UI work."""

from .contracts import (
    UiScreenDefinition,
    UiScreenId,
    UiTransportBoundary,
    UiTransportKind,
    UiTransportStatus,
    build_default_ui_boundary,
    build_ui_screen_manifest,
)
from .graphfakos_adapter import PragmaGraphViewerProvider
from .local_server import (
    LocalVisualHttpServer,
    LocalVisualServerResult,
    RenderPath,
    make_local_visual_server,
    serve_local_visual_server,
)
from .preview import (
    PreviewScreen,
    UiPreviewRender,
    UiPreviewRequest,
    UiPreviewResult,
    make_ui_preview_server,
    render_ui_preview,
    serve_ui_preview,
    write_ui_preview,
)

__all__ = [
    "LocalVisualHttpServer",
    "LocalVisualServerResult",
    "PreviewScreen",
    "PragmaGraphViewerProvider",
    "RenderPath",
    "UiPreviewRender",
    "UiPreviewRequest",
    "UiPreviewResult",
    "UiScreenDefinition",
    "UiScreenId",
    "UiTransportBoundary",
    "UiTransportKind",
    "UiTransportStatus",
    "build_default_ui_boundary",
    "build_ui_screen_manifest",
    "make_local_visual_server",
    "make_ui_preview_server",
    "render_ui_preview",
    "serve_local_visual_server",
    "serve_ui_preview",
    "write_ui_preview",
]
