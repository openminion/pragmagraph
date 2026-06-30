"""Document-link navigation facts over observed snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping
from pragmagraph.contracts import (
    EDGE_MENTIONS,
    EDGE_REFERENCES_DOC,
    EDGE_REFERENCES_SECTION,
    NODE_DOC_SECTION,
    NODE_FILE,
)
from pragmagraph.models import GraphNode, GraphSnapshot, SourceRef


@dataclass(frozen=True)
class DocReferenceTarget:
    """One document target with incoming structural references."""

    node_id: str
    label: str
    source_ref: SourceRef = field(default_factory=SourceRef)
    incoming_count: int = 0
    referrer_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "referrer_ids", tuple(self.referrer_ids))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "source_ref": self.source_ref.to_dict(),
            "incoming_count": self.incoming_count,
            "referrer_ids": list(self.referrer_ids),
        }


@dataclass(frozen=True)
class DocMentionCandidate:
    """One unresolved document mention candidate."""

    doc_node_id: str
    candidate_node_id: str
    token: str
    source_ref: SourceRef = field(default_factory=SourceRef)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_node_id": self.doc_node_id,
            "candidate_node_id": self.candidate_node_id,
            "token": self.token,
            "source_ref": self.source_ref.to_dict(),
        }


@dataclass(frozen=True)
class DocGraphSummary:
    """Deterministic document graph summary."""

    namespace: str
    doc_section_count: int
    linked_doc_target_count: int
    unlinked_candidate_count: int
    top_targets: tuple[DocReferenceTarget, ...] = ()
    unlinked_candidates: tuple[DocMentionCandidate, ...] = ()
    edge_kinds: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "top_targets", tuple(self.top_targets))
        object.__setattr__(self, "unlinked_candidates", tuple(self.unlinked_candidates))
        object.__setattr__(self, "edge_kinds", frozen_mapping(self.edge_kinds))

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "doc_section_count": self.doc_section_count,
            "linked_doc_target_count": self.linked_doc_target_count,
            "unlinked_candidate_count": self.unlinked_candidate_count,
            "top_targets": [item.to_dict() for item in self.top_targets],
            "unlinked_candidates": [
                item.to_dict() for item in self.unlinked_candidates
            ],
            "edge_kinds": dict(self.edge_kinds),
        }


def build_doc_graph_summary(
    snapshot: GraphSnapshot,
    *,
    top_n: int = 10,
) -> DocGraphSummary:
    """Build document-link and unresolved-mention facts."""
    limit = max(1, int(top_n or 1))
    node_map = snapshot.node_map()
    doc_nodes = [node for node in snapshot.nodes if node.kind == NODE_DOC_SECTION]
    doc_edges = [
        edge
        for edge in snapshot.edges
        if edge.kind in {EDGE_MENTIONS, EDGE_REFERENCES_DOC, EDGE_REFERENCES_SECTION}
    ]
    incoming: dict[str, list[str]] = defaultdict(list)
    for edge in doc_edges:
        incoming[edge.target_id].append(edge.source_id)
    top_targets = [
        DocReferenceTarget(
            node_id=node_id,
            label=node_map[node_id].label,
            source_ref=node_map[node_id].source_ref,
            incoming_count=len(referrers),
            referrer_ids=tuple(sorted(set(referrers))[:limit]),
        )
        for node_id, referrers in incoming.items()
        if node_id in node_map and node_map[node_id].kind == NODE_DOC_SECTION
    ]
    top_targets.sort(key=lambda item: (-item.incoming_count, item.node_id))
    candidates = _unlinked_candidates(snapshot, doc_nodes, limit=limit)
    return DocGraphSummary(
        namespace=snapshot.namespace,
        doc_section_count=len(doc_nodes),
        linked_doc_target_count=len(top_targets),
        unlinked_candidate_count=len(candidates),
        top_targets=tuple(top_targets[:limit]),
        unlinked_candidates=tuple(candidates[:limit]),
        edge_kinds=dict(Counter(edge.kind for edge in doc_edges)),
    )


def render_markdown_doc_graph(summary: DocGraphSummary) -> str:
    """Render document-link facts as Markdown."""
    lines = [
        "# PragmaGraph Document Graph",
        "",
        f"- Namespace: `{summary.namespace}`",
        f"- Doc sections: `{summary.doc_section_count}`",
        f"- Linked doc targets: `{summary.linked_doc_target_count}`",
        f"- Unlinked mention candidates: `{summary.unlinked_candidate_count}`",
        "",
        "## Top Linked Targets",
        "",
    ]
    lines.extend(
        f"- `{target.node_id}` ({target.incoming_count} incoming)"
        for target in summary.top_targets
    )
    if summary.unlinked_candidates:
        lines.extend(["", "## Unlinked Mention Candidates", ""])
        lines.extend(
            f"- `{item.token}` in `{item.doc_node_id}` -> `{item.candidate_node_id}`"
            for item in summary.unlinked_candidates
        )
    return "\n".join(lines).rstrip() + "\n"


def _unlinked_candidates(
    snapshot: GraphSnapshot,
    doc_nodes: list[GraphNode],
    *,
    limit: int,
) -> list[DocMentionCandidate]:
    existing = {
        (edge.source_id, edge.target_id)
        for edge in snapshot.edges
        if edge.kind in {EDGE_MENTIONS, EDGE_REFERENCES_DOC, EDGE_REFERENCES_SECTION}
    }
    candidate_nodes = [
        node
        for node in snapshot.nodes
        if node.kind != NODE_DOC_SECTION
        and node.kind != NODE_FILE
        and node.label
        and len(node.label) >= 4
    ]
    results: list[DocMentionCandidate] = []
    for doc in doc_nodes:
        haystack = f"{doc.label} {doc.text}".lower()
        for candidate in candidate_nodes:
            token = candidate.label.strip()
            if not token or token.lower() not in haystack:
                continue
            if (doc.id, candidate.id) in existing:
                continue
            results.append(
                DocMentionCandidate(
                    doc_node_id=doc.id,
                    candidate_node_id=candidate.id,
                    token=token,
                    source_ref=doc.source_ref,
                )
            )
            if len(results) >= limit:
                return sorted(results, key=lambda item: (item.doc_node_id, item.token))
    return sorted(results, key=lambda item: (item.doc_node_id, item.token))


__all__ = [
    "DocGraphSummary",
    "DocMentionCandidate",
    "DocReferenceTarget",
    "build_doc_graph_summary",
    "render_markdown_doc_graph",
]
