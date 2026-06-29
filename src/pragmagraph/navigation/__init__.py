"""Compact navigation views over observed PragmaGraph snapshots."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph.contracts import (
    EDGE_CONTAINS,
    NODE_DIRECTORY,
    NODE_DOC_SECTION,
    NODE_FILE,
    NODE_GIT_COMMIT,
    NODE_PROJECT,
)
from pragmagraph.models import GraphNode, GraphSnapshot


@dataclass(frozen=True)
class RepoMapSection:
    """One compact section in a repository map."""

    title: str
    items: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", str(self.title))
        object.__setattr__(self, "items", tuple(str(item) for item in self.items))

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "items": list(self.items)}


@dataclass(frozen=True)
class RepoMap:
    """Human-sized navigation summary for one observed snapshot."""

    namespace: str
    root_path: str
    sections: tuple[RepoMapSection, ...] = ()
    stats: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "namespace", str(self.namespace))
        object.__setattr__(self, "root_path", str(self.root_path))
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "stats", dict(self.stats))

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "root_path": self.root_path,
            "sections": [section.to_dict() for section in self.sections],
            "stats": dict(self.stats),
        }


def build_repo_map(snapshot: GraphSnapshot, *, top_n: int = 8) -> RepoMap:
    """Build a deterministic compact map for fast human or agent navigation."""
    limit = max(1, int(top_n or 1))
    node_kinds = Counter(node.kind for node in snapshot.nodes)
    edge_kinds = Counter(edge.kind for edge in snapshot.edges)
    omitted_reasons = Counter(item.reason for item in snapshot.omitted)
    directories = _top_directories(snapshot, limit=limit)
    files = _top_files(snapshot, limit=limit)
    symbols = _top_symbols(snapshot, limit=limit)
    docs = _top_doc_sections(snapshot, limit=limit)
    commits = _top_commits(snapshot, limit=limit)
    sections = (
        RepoMapSection("Directories", directories),
        RepoMapSection("Files", files),
        RepoMapSection("Symbols", symbols),
        RepoMapSection("Docs", docs),
        RepoMapSection("Recent Git Commits", commits),
        RepoMapSection(
            "Omitted",
            tuple(
                f"{reason}: {count}"
                for reason, count in sorted(omitted_reasons.items())
            ),
        ),
    )
    return RepoMap(
        namespace=snapshot.namespace,
        root_path=snapshot.root_path,
        sections=sections,
        stats={
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "omitted_count": len(snapshot.omitted),
            "node_kinds": dict(sorted(node_kinds.items())),
            "edge_kinds": dict(sorted(edge_kinds.items())),
            "parser_set": list(snapshot.stats.get("parser_set", ())),
        },
    )


def render_markdown_repo_map(repo_map: RepoMap) -> str:
    """Render a compact repository map as Markdown."""
    lines = [
        "# PragmaGraph Repo Map",
        "",
        f"- Namespace: `{repo_map.namespace}`",
        f"- Root: `{repo_map.root_path}`",
        f"- Nodes: `{repo_map.stats.get('node_count', 0)}`",
        f"- Edges: `{repo_map.stats.get('edge_count', 0)}`",
        f"- Omitted: `{repo_map.stats.get('omitted_count', 0)}`",
        "",
    ]
    for section in repo_map.sections:
        if not section.items:
            continue
        lines.append(f"## {section.title}")
        lines.append("")
        lines.extend(f"- {item}" for item in section.items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_compact_handoff(snapshot: GraphSnapshot, *, top_n: int = 6) -> str:
    """Render a short handoff note for an agent about one snapshot."""
    repo_map = build_repo_map(snapshot, top_n=top_n)
    stats = repo_map.stats
    lines = [
        "# PragmaGraph Compact Handoff",
        "",
        "Use this as a fast structural orientation aid. It contains observed facts",
        "only; it does not infer owner intent, risk, or architectural judgment.",
        "",
        "## Snapshot",
        "",
        f"- Namespace: `{repo_map.namespace}`",
        f"- Nodes / edges: `{stats.get('node_count', 0)}` / `{stats.get('edge_count', 0)}`",
        f"- Omitted facts: `{stats.get('omitted_count', 0)}`",
        f"- Parsers: `{', '.join(stats.get('parser_set', ())) or 'none'}`",
        "",
    ]
    for section in repo_map.sections[:4]:
        if not section.items:
            continue
        lines.append(f"## {section.title}")
        lines.append("")
        lines.extend(f"- {item}" for item in section.items[:top_n])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _top_directories(snapshot: GraphSnapshot, *, limit: int) -> tuple[str, ...]:
    child_counts: Counter[str] = Counter()
    node_map = snapshot.node_map()
    for edge in snapshot.edges:
        if edge.kind != EDGE_CONTAINS:
            continue
        node = node_map.get(edge.source_id)
        if node is not None and node.kind in {NODE_PROJECT, NODE_DIRECTORY}:
            child_counts[node.source_ref.path or "."] += 1
    return tuple(
        f"{path or '.'} ({count} children)"
        for path, count in sorted(
            child_counts.items(), key=lambda item: (-item[1], item[0])
        )[:limit]
    )


def _top_files(snapshot: GraphSnapshot, *, limit: int) -> tuple[str, ...]:
    files = [
        node.source_ref.path
        for node in snapshot.nodes
        if node.kind == NODE_FILE and node.source_ref.path
    ]
    return tuple(sorted(files)[:limit])


def _top_symbols(snapshot: GraphSnapshot, *, limit: int) -> tuple[str, ...]:
    symbols = [_format_node(node) for node in snapshot.nodes if _is_symbol_node(node)]
    return tuple(sorted(symbols)[:limit])


def _top_doc_sections(snapshot: GraphSnapshot, *, limit: int) -> tuple[str, ...]:
    sections = [
        _format_node(node) for node in snapshot.nodes if node.kind == NODE_DOC_SECTION
    ]
    return tuple(sorted(sections)[:limit])


def _top_commits(snapshot: GraphSnapshot, *, limit: int) -> tuple[str, ...]:
    commits = [node for node in snapshot.nodes if node.kind == NODE_GIT_COMMIT]
    commits.sort(
        key=lambda node: (
            -int(node.metadata.get("committer_time_epoch", 0) or 0),
            node.id,
        )
    )
    return tuple(_format_commit(node) for node in commits[:limit])


def _format_node(node: GraphNode) -> str:
    location = node.source_ref.path or "."
    line = f":{node.source_ref.line}" if node.source_ref.line else ""
    return f"{node.label} ({node.kind}, {location}{line})"


def _is_symbol_node(node: GraphNode) -> bool:
    return node.kind.endswith(("_function", "_class", "_method", "_export"))


def _format_commit(node: GraphNode) -> str:
    short_hash = str(node.metadata.get("short_commit_hash", "") or node.label)
    subject = str(node.metadata.get("subject", "") or node.label)
    return f"{short_hash} {subject}"


__all__ = [
    "RepoMap",
    "RepoMapSection",
    "build_repo_map",
    "render_compact_handoff",
    "render_markdown_repo_map",
]
