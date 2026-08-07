"""Viewer envelope DTO and stable JSON persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

VIEWER_ENVELOPE_SCHEMA_VERSION = "pragmagraph.viewer.v1alpha1"
VIEWER_FIXTURE_SCENARIOS = ("viewer-scale-1k", "viewer-scale-200k", "viewer-scale-1m")

DEFAULT_GENERATED_AT = "2026-07-06T00:00:00+00:00"


@dataclass(frozen=True)
class ViewerGraphEnvelope:
    """Stable JSON envelope consumed by provider-neutral graph viewers."""

    schema_version: str
    producer: Mapping[str, Any]
    snapshot_id: str
    snapshot_version: str
    root_identity: Mapping[str, Any]
    generated_at: str
    graph_stats: Mapping[str, Any]
    render_hint: Mapping[str, Any]
    level_of_detail: str
    nodes: tuple[Mapping[str, Any], ...] = ()
    edges: tuple[Mapping[str, Any], ...] = ()
    clusters: tuple[Mapping[str, Any], ...] = ()
    edge_bundles: tuple[Mapping[str, Any], ...] = ()
    omitted: tuple[Mapping[str, Any], ...] = ()
    expansion: tuple[Mapping[str, Any], ...] = ()
    content_index: Mapping[str, Any] = field(default_factory=dict)
    evidence_index: Mapping[str, Any] = field(default_factory=dict)
    provenance: tuple[Mapping[str, Any], ...] = ()
    capabilities: Mapping[str, Any] = field(default_factory=dict)
    compatibility: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "producer": dict(self.producer),
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "root_identity": dict(self.root_identity),
            "generated_at": self.generated_at,
            "graph_stats": dict(self.graph_stats),
            "render_hint": dict(self.render_hint),
            "level_of_detail": self.level_of_detail,
            "nodes": [dict(item) for item in self.nodes],
            "edges": [dict(item) for item in self.edges],
            "clusters": [dict(item) for item in self.clusters],
            "edge_bundles": [dict(item) for item in self.edge_bundles],
            "omitted": [dict(item) for item in self.omitted],
            "expansion": [dict(item) for item in self.expansion],
            "content_index": dict(self.content_index),
            "evidence_index": dict(self.evidence_index),
            "provenance": [dict(item) for item in self.provenance],
            "capabilities": dict(self.capabilities),
            "compatibility": dict(self.compatibility),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ViewerGraphEnvelope":
        return cls(
            schema_version=str(payload.get("schema_version") or ""),
            producer=dict(payload.get("producer") or {}),
            snapshot_id=str(payload.get("snapshot_id") or ""),
            snapshot_version=str(payload.get("snapshot_version") or ""),
            root_identity=dict(payload.get("root_identity") or {}),
            generated_at=str(payload.get("generated_at") or ""),
            graph_stats=dict(payload.get("graph_stats") or {}),
            render_hint=dict(payload.get("render_hint") or {}),
            level_of_detail=str(payload.get("level_of_detail") or "raw"),
            nodes=tuple(dict(item) for item in payload.get("nodes") or ()),
            edges=tuple(dict(item) for item in payload.get("edges") or ()),
            clusters=tuple(dict(item) for item in payload.get("clusters") or ()),
            edge_bundles=tuple(
                dict(item) for item in payload.get("edge_bundles") or ()
            ),
            omitted=tuple(dict(item) for item in payload.get("omitted") or ()),
            expansion=tuple(dict(item) for item in payload.get("expansion") or ()),
            content_index=dict(payload.get("content_index") or {}),
            evidence_index=dict(payload.get("evidence_index") or {}),
            provenance=tuple(dict(item) for item in payload.get("provenance") or ()),
            capabilities=dict(payload.get("capabilities") or {}),
            compatibility=dict(payload.get("compatibility") or {}),
        )


def load_viewer_envelope(path: str) -> ViewerGraphEnvelope:
    payload = json.loads(Path(path).expanduser().resolve(strict=True).read_text())
    return ViewerGraphEnvelope.from_dict(payload)


def write_viewer_envelope(envelope: ViewerGraphEnvelope, out: str) -> dict[str, Any]:
    path = Path(out).expanduser().resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(envelope.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "output_path": str(path),
        "schema_version": envelope.schema_version,
        "snapshot_id": envelope.snapshot_id,
        "level_of_detail": envelope.level_of_detail,
        "raw_node_count": envelope.graph_stats.get("raw_node_count", 0),
        "visible_node_count": len(envelope.nodes),
        "cluster_count": len(envelope.clusters),
    }


def viewer_capabilities() -> Mapping[str, Any]:
    return {
        "content_preview": True,
        "full_content_lookup": True,
        "cluster_expand": True,
        "neighborhood": True,
        "path": True,
        "edit_commands": ("note_draft", "tag_draft", "pin_draft", "evidence_request"),
        "durable_mutation": False,
    }


def viewer_compatibility() -> Mapping[str, Any]:
    return {
        "viewer": "graphfakos",
        "static_fallback": True,
        "requires_pragmagraph_import_in_viewer": False,
        "large_raw_nodes_embedded_by_default": False,
    }


def color_hint(index: int) -> str:
    palette = ("#45d1c6", "#7cc957", "#9e7cff", "#ff9b52", "#6ab3ff", "#ef6f82")
    return palette[index % len(palette)]
