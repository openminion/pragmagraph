"""Observed-fact delta payloads for the local PragmaGraph workbench."""

from __future__ import annotations

from pathlib import Path

from pragmagraph.models import GraphSnapshot
from pragmagraph.refresh import build_ci_delta
from pragmagraph.storage import load_snapshot
from pragmagraph.workspace import load_workspace_status

from .preview_types import UiPreviewRequest

DELTA_REVIEW_SCHEMA_VERSION = "pragmagraph.delta_review.v1alpha1"


def build_delta_review_payload(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> dict[str, object]:
    """Build deterministic delta-review facts without inferring risk or intent."""
    payload: dict[str, object] = {
        "schema_version": DELTA_REVIEW_SCHEMA_VERSION,
        "boundary": "observed_facts_only",
        "mode": "current_snapshot",
        "current": _snapshot_summary(snapshot),
        "delta": {},
        "refresh_status": {},
        "diagnostics": [],
    }
    diagnostics: list[str] = []
    before = _load_optional_snapshot(request.before_snapshot, diagnostics)
    after = _load_optional_snapshot(request.after_snapshot, diagnostics) or snapshot
    if before is not None:
        payload["mode"] = "snapshot_compare"
        payload["before"] = _snapshot_summary(before)
        payload["after"] = _snapshot_summary(after)
        payload["delta"] = build_ci_delta(before, after).to_dict()
    elif request.workspace:
        payload["mode"] = "workspace_refresh_status"
        status = load_workspace_status(request.workspace)
        payload["refresh_status"] = (
            status.refresh_status.to_dict() if status.refresh_status is not None else {}
        )
    else:
        diagnostics.append("before_snapshot_not_provided")
    payload["diagnostics"] = diagnostics
    return payload


def _load_optional_snapshot(
    path: str | None,
    diagnostics: list[str],
) -> GraphSnapshot | None:
    if not path:
        return None
    target = Path(path)
    if not target.exists():
        diagnostics.append(f"snapshot_not_found:{path}")
        return None
    return load_snapshot(target)


def _snapshot_summary(snapshot: GraphSnapshot) -> dict[str, object]:
    return {
        "namespace": snapshot.namespace,
        "root_path": snapshot.root_path,
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "omitted_count": len(snapshot.omitted),
        "created_at": snapshot.created_at,
        "schema_version": snapshot.schema_version,
        "indexer_version": snapshot.indexer_version,
    }


__all__ = ["DELTA_REVIEW_SCHEMA_VERSION", "build_delta_review_payload"]
