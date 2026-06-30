"""Observed git path-lineage helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping
from pragmagraph.contracts import (
    EDGE_GIT_CHANGES_PATH,
    NODE_GIT_CHANGED_PATH,
    NODE_GIT_COMMIT,
)
from pragmagraph.models import GraphNode, GraphSnapshot, SourceRef


@dataclass(frozen=True)
class GitLineageEntry:
    """One observed commit/path change in a path lineage."""

    commit_hash: str
    short_commit_hash: str
    path: str
    previous_path: str = ""
    change_kind: str = "modify"
    subject: str = ""
    committer_time_epoch: int = 0
    committer_time_offset: str = ""
    source_ref: SourceRef = field(default_factory=SourceRef)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", frozen_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "commit_hash": self.commit_hash,
            "short_commit_hash": self.short_commit_hash,
            "path": self.path,
            "previous_path": self.previous_path,
            "change_kind": self.change_kind,
            "subject": self.subject,
            "committer_time_epoch": self.committer_time_epoch,
            "committer_time_offset": self.committer_time_offset,
            "source_ref": self.source_ref.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class GitLineage:
    """Observed lineage for one relative path."""

    query_path: str
    entries: tuple[GitLineageEntry, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(self, "diagnostics", frozen_mapping(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_path": self.query_path,
            "entries": [item.to_dict() for item in self.entries],
            "diagnostics": dict(self.diagnostics),
        }


def build_git_lineage(
    snapshot: GraphSnapshot,
    path: str,
    *,
    max_results: int = 20,
) -> GitLineage:
    """Return observed git path lineage without inferring commit intent."""
    commit_nodes = {
        node.id: node for node in snapshot.nodes if node.kind == NODE_GIT_COMMIT
    }
    changed_path_nodes = {
        node.id: node for node in snapshot.nodes if node.kind == NODE_GIT_CHANGED_PATH
    }
    path_cursor = path.strip()
    entries: list[GitLineageEntry] = []
    seen: set[tuple[str, str]] = set()
    change_edges = [
        edge for edge in snapshot.edges if edge.kind == EDGE_GIT_CHANGES_PATH
    ]
    change_edges.sort(
        key=lambda edge: (-_commit_epoch(commit_nodes, edge.source_id), edge.id)
    )
    for edge in change_edges:
        if edge.kind != EDGE_GIT_CHANGES_PATH:
            continue
        changed_node = changed_path_nodes.get(edge.target_id)
        commit_node = commit_nodes.get(edge.source_id)
        if changed_node is None or commit_node is None:
            continue
        changed_path = changed_node.source_ref.path
        previous_path = str(
            edge.metadata.get("previous_path")
            or changed_node.metadata.get("previous_path")
            or ""
        )
        if changed_path != path_cursor and previous_path != path_cursor:
            continue
        key = (str(commit_node.metadata.get("commit_hash", "")), changed_path)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            GitLineageEntry(
                commit_hash=str(commit_node.metadata.get("commit_hash", "")),
                short_commit_hash=str(
                    commit_node.metadata.get("short_commit_hash", commit_node.label)
                ),
                path=changed_path,
                previous_path=previous_path,
                change_kind=str(edge.metadata.get("change_kind", "modify")),
                subject=str(commit_node.metadata.get("subject", "")),
                committer_time_epoch=int(
                    commit_node.metadata.get("committer_time_epoch", 0) or 0
                ),
                committer_time_offset=str(
                    commit_node.metadata.get("committer_time_offset", "")
                ),
                source_ref=edge.source_ref,
                metadata={
                    "additions": edge.metadata.get("additions"),
                    "deletions": edge.metadata.get("deletions"),
                },
            )
        )
        if previous_path:
            path_cursor = previous_path
    entries.sort(key=lambda item: (-item.committer_time_epoch, item.commit_hash))
    return GitLineage(
        query_path=path,
        entries=tuple(entries[: max(1, int(max_results or 1))]),
        diagnostics={
            "git_overlay_enabled": bool(snapshot.stats.get("git_overlay_enabled")),
            "entry_count": len(entries),
            "truncated": len(entries) > max_results,
        },
    )


def _commit_epoch(commit_nodes: Mapping[str, GraphNode], commit_id: str) -> int:
    node = commit_nodes.get(commit_id)
    if node is None:
        return 0
    return int(node.metadata.get("committer_time_epoch", 0) or 0)


__all__ = ["GitLineage", "GitLineageEntry", "build_git_lineage"]
