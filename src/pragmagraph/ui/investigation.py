"""Observed-fact investigation payloads for the local PragmaGraph workbench."""

from __future__ import annotations

from typing import Any, cast

from pragmagraph.investigate import (
    INVESTIGATION_PRESETS,
    InvestigationPreset,
    build_investigation_bundle,
)
from pragmagraph.models import GraphSnapshot

from .preview_types import UiPreviewRequest


def build_investigation_payload(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> dict[str, Any]:
    """Build one guided graph-inspection payload for visual review."""
    preset = (
        request.investigation_preset
        if request.investigation_preset in INVESTIGATION_PRESETS
        else "search"
    )
    return build_investigation_bundle(
        snapshot,
        request.query,
        snapshot_path=request.snapshot or "",
        preset=cast(InvestigationPreset, preset),
        max_results=request.max_results,
    ).to_dict()


__all__ = ["build_investigation_payload"]
