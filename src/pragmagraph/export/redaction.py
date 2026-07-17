"""Deterministic export-time projections over canonical snapshots."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from pragmagraph.models import GraphNode, GraphSnapshot

EXPORT_PROFILE_FULL = "full"
EXPORT_PROFILE_NO_CONTENT = "no_content"
EXPORT_PROFILE_NO_IDENTITIES = "no_identities"
EXPORT_PROFILE_PORTABLE = "portable"
EXPORT_PROFILES = frozenset(
    {
        EXPORT_PROFILE_FULL,
        EXPORT_PROFILE_NO_CONTENT,
        EXPORT_PROFILE_NO_IDENTITIES,
        EXPORT_PROFILE_PORTABLE,
    }
)

IDENTITY_KEYS = frozenset(
    {
        "author_email",
        "author_email_hash",
        "author_name",
        "committer_email",
        "committer_email_hash",
        "committer_name",
    }
)
CONTENT_KEYS = frozenset({"content", "raw", "snippet", "subject", "value"})


@dataclass(frozen=True)
class ExportProjection:
    """One derived export and its explicit redaction evidence."""

    snapshot: GraphSnapshot
    profile: str
    redacted_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "redacted_fields": list(self.redacted_fields),
            "snapshot": self.snapshot.to_dict(),
        }


def project_snapshot(
    snapshot: GraphSnapshot,
    *,
    profile: str = EXPORT_PROFILE_FULL,
) -> ExportProjection:
    """Return a non-mutating, deterministic export projection."""
    normalized = str(profile or EXPORT_PROFILE_FULL).strip().lower()
    if normalized not in EXPORT_PROFILES:
        supported = ", ".join(sorted(EXPORT_PROFILES))
        raise ValueError(
            f"unsupported export profile {profile!r}; expected {supported}"
        )
    if normalized == EXPORT_PROFILE_FULL:
        return ExportProjection(snapshot=snapshot, profile=normalized)
    fields: set[str] = set()
    nodes = tuple(
        _project_node(node, profile=normalized, redacted_fields=fields)
        for node in snapshot.nodes
    )
    edges = tuple(
        replace(
            edge,
            metadata=_project_metadata(
                edge.metadata,
                profile=normalized,
                redacted_fields=fields,
            ),
        )
        for edge in snapshot.edges
    )
    root_path = snapshot.root_path
    stats = dict(snapshot.stats)
    if normalized == EXPORT_PROFILE_PORTABLE and root_path:
        root_path = ""
        fields.add("snapshot.root_path")
    if normalized == EXPORT_PROFILE_PORTABLE:
        stats = _portable_stats(stats, redacted_fields=fields)
    return ExportProjection(
        snapshot=replace(
            snapshot,
            root_path=root_path,
            nodes=nodes,
            edges=edges,
            stats=stats,
        ),
        profile=normalized,
        redacted_fields=tuple(sorted(fields)),
    )


def _project_node(
    node: GraphNode,
    *,
    profile: str,
    redacted_fields: set[str],
) -> GraphNode:
    metadata = _project_metadata(
        node.metadata,
        profile=profile,
        redacted_fields=redacted_fields,
    )
    text = node.text
    label = node.label
    if profile == EXPORT_PROFILE_NO_CONTENT:
        if text:
            redacted_fields.add("node.text")
        if label:
            redacted_fields.add("node.label")
        text = ""
        label = node.kind
    return replace(node, text=text, label=label, metadata=metadata)


def _project_metadata(
    metadata: Mapping[str, Any],
    *,
    profile: str,
    redacted_fields: set[str],
) -> dict[str, Any]:
    blocked = IDENTITY_KEYS if profile == EXPORT_PROFILE_NO_IDENTITIES else frozenset()
    if profile == EXPORT_PROFILE_NO_CONTENT:
        blocked |= CONTENT_KEYS
    result = {}
    for key, value in metadata.items():
        if key in blocked:
            redacted_fields.add(f"metadata.{key}")
            continue
        result[key] = value
    return result


def _portable_stats(
    stats: Mapping[str, Any],
    *,
    redacted_fields: set[str],
) -> dict[str, Any]:
    result = dict(stats)
    raw_report = result.get("precise_ingestion")
    if not isinstance(raw_report, Mapping):
        return result
    report = dict(raw_report)
    if report.get("project_root"):
        report["project_root"] = ""
        redacted_fields.add("stats.precise_ingestion.project_root")
    raw_freshness = report.get("freshness")
    if isinstance(raw_freshness, Mapping):
        freshness = dict(raw_freshness)
        for key in ("index_root", "workspace_root"):
            if freshness.get(key):
                freshness[key] = ""
                redacted_fields.add(f"stats.precise_ingestion.freshness.{key}")
        report["freshness"] = freshness
    result["precise_ingestion"] = report
    return result


__all__ = [
    "EXPORT_PROFILES",
    "EXPORT_PROFILE_FULL",
    "EXPORT_PROFILE_NO_CONTENT",
    "EXPORT_PROFILE_NO_IDENTITIES",
    "EXPORT_PROFILE_PORTABLE",
    "ExportProjection",
    "project_snapshot",
]
