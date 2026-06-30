"""Typed request and result contracts for local UI preview helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
    artifact_path: str = ""
    embed_path: str = ""
    report_path: str = ""
    markdown_report_path: str = ""
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
    provider_id: str
    route: str
    artifact: dict[str, object] | None = None
    embed: dict[str, object] | None = None
    report: dict[str, object] | None = None
    markdown_report: dict[str, object] | None = None
    opened: bool = False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "output_path": self.output_path,
            "screen": self.screen,
            "workspace": self.workspace,
            "snapshot": self.snapshot,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "provider_id": self.provider_id,
            "route": self.route,
            "opened": self.opened,
        }
        if self.artifact is not None:
            payload["artifact"] = self.artifact
        if self.embed is not None:
            payload["embed"] = self.embed
        if self.report is not None:
            payload["report"] = self.report
        if self.markdown_report is not None:
            payload["markdown_report"] = self.markdown_report
        return payload


@dataclass(frozen=True, slots=True)
class UiPreviewRender:
    """HTML render result for the local visual preview."""

    html: str
    screen: str
    workspace: str | None
    snapshot: str | None
    node_count: int
    edge_count: int


__all__ = [
    "PreviewScreen",
    "UiPreviewRender",
    "UiPreviewRequest",
    "UiPreviewResult",
]
