"""Read-only graph-pack review payloads for the local PragmaGraph workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pragmagraph.portability import review_graph_pack

from .preview_types import UiPreviewRequest

GRAPH_PACK_REVIEW_SCHEMA_VERSION = "pragmagraph.ui_graph_pack_review.v1alpha1"


def build_graph_pack_review_payload(request: UiPreviewRequest) -> dict[str, Any]:
    """Build receive-side graph-pack facts without importing files."""
    if not request.graph_pack_path:
        return _unavailable_payload(
            pack_path="",
            diagnostics=("graph_pack_not_provided",),
        )
    pack_path = Path(request.graph_pack_path)
    if not pack_path.exists():
        return _unavailable_payload(
            pack_path=str(pack_path),
            diagnostics=("graph_pack_not_found",),
        )
    review = review_graph_pack(
        pack_path,
        snapshot_out=request.snapshot_out,
        store_out=request.store_out,
    ).to_dict()
    return {
        "schema_version": GRAPH_PACK_REVIEW_SCHEMA_VERSION,
        "boundary": "observed_facts_only",
        "mode": "receive_review",
        "review": review,
        "diagnostics": [],
    }


def _unavailable_payload(
    *,
    pack_path: str,
    diagnostics: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": GRAPH_PACK_REVIEW_SCHEMA_VERSION,
        "boundary": "observed_facts_only",
        "mode": "unavailable",
        "pack_path": pack_path,
        "diagnostics": list(diagnostics),
    }


__all__ = ["GRAPH_PACK_REVIEW_SCHEMA_VERSION", "build_graph_pack_review_payload"]
