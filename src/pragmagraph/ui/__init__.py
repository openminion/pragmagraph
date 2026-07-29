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
from .evidence import (
    AGENT_CONTEXT_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    build_evidence_payload,
    render_agent_context,
    write_agent_context,
    write_evidence_payload,
)
from .delta_review import DELTA_REVIEW_SCHEMA_VERSION, build_delta_review_payload
from .graph_pack import (
    GRAPH_PACK_REVIEW_SCHEMA_VERSION,
    build_graph_pack_review_payload,
)
from .graphfakos_adapter import PragmaGraphLiveViewerProvider, PragmaGraphViewerProvider
from .investigation import build_investigation_payload
from .local_server import (
    LocalVisualHttpServer,
    LocalVisualServerResult,
    RenderPath,
    make_local_visual_server,
    serve_local_visual_server,
)
from .preview import (
    make_ui_preview_server,
    render_ui_preview,
    serve_ui_preview,
    write_ui_preview,
)
from .preview_types import (
    PreviewScreen,
    UiPreviewRender,
    UiPreviewRequest,
    UiPreviewResult,
)

__all__ = [
    "AGENT_CONTEXT_SCHEMA_VERSION",
    "DELTA_REVIEW_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "GRAPH_PACK_REVIEW_SCHEMA_VERSION",
    "LocalVisualHttpServer",
    "LocalVisualServerResult",
    "PragmaGraphLiveViewerProvider",
    "PragmaGraphViewerProvider",
    "PreviewScreen",
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
    "build_delta_review_payload",
    "build_evidence_payload",
    "build_graph_pack_review_payload",
    "build_investigation_payload",
    "build_ui_screen_manifest",
    "make_local_visual_server",
    "make_ui_preview_server",
    "render_agent_context",
    "render_ui_preview",
    "serve_local_visual_server",
    "serve_ui_preview",
    "write_agent_context",
    "write_evidence_payload",
    "write_ui_preview",
]
