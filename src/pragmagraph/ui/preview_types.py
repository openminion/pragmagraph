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


__all__ = [
    "PreviewScreen",
    "UiPreviewRender",
    "UiPreviewRequest",
    "UiPreviewResult",
]
