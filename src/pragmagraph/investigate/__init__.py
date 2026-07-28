"""Guided observed-fact investigation bundles over PragmaGraph snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, QueryRequest
from pragmagraph.query import health, neighborhood, path, query

InvestigationPreset = Literal[
    "search",
    "file_map",
    "symbol_map",
    "doc_links",
    "changed_recently",
    "orphans",
    "high_degree",
]

INVESTIGATION_SCHEMA_VERSION = "pragmagraph.investigation.v1alpha1"
INVESTIGATION_PRESETS: tuple[InvestigationPreset, ...] = (
    "search",
    "file_map",
    "symbol_map",
    "doc_links",
    "changed_recently",
    "orphans",
    "high_degree",
)


@dataclass(frozen=True, slots=True)
class InvestigationBundle:
    """One deterministic navigation bundle for a static graph question."""

    schema_version: str
    boundary: str
    query: str
    preset: str
    health: Mapping[str, Any]
    matches: tuple[Mapping[str, Any], ...] = ()
    related: Mapping[str, tuple[Mapping[str, Any], ...]] = field(default_factory=dict)
    neighborhood: Mapping[str, Any] = field(default_factory=dict)
    path: Mapping[str, Any] = field(default_factory=dict)
    freshness: Mapping[str, Any] = field(default_factory=dict)
    next_commands: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "boundary": self.boundary,
            "query": self.query,
            "preset": self.preset,
            "health": dict(self.health),
            "matches": [dict(item) for item in self.matches],
            "related": {
                key: [dict(item) for item in values]
                for key, values in self.related.items()
            },
            "neighborhood": dict(self.neighborhood),
            "path": dict(self.path),
            "freshness": dict(self.freshness),
            "next_commands": {
                key: list(command) for key, command in self.next_commands.items()
            },
        }


def build_investigation_bundle(
    snapshot: GraphSnapshot,
    query_text: str,
    *,
    snapshot_path: str = "",
    preset: InvestigationPreset = "search",
    max_results: int = 5,
) -> InvestigationBundle:
    """Build a compact graph-navigation bundle without semantic inference."""
    selected_nodes = _preset_nodes(snapshot, preset)
    result = query(
        GraphSnapshot(
            namespace=snapshot.namespace,
            root_path=snapshot.root_path,
            nodes=selected_nodes,
            edges=snapshot.edges,
            omitted=snapshot.omitted,
            stats=snapshot.stats,
            schema_version=snapshot.schema_version,
            indexer_version=snapshot.indexer_version,
            created_at=snapshot.created_at,
        ),
        QueryRequest(query=query_text, max_results=max_results),
    )
    result_payload = result.to_dict()
    matches = tuple(_match_payload(hit.to_dict()) for hit in result.hits)
    first_node_id = _node_id(matches, 0)
    second_node_id = _node_id(matches, 1)
    neighborhood_payload = (
        neighborhood(
            snapshot, first_node_id, depth=1, max_results=max_results
        ).to_dict()
        if first_node_id
        else {}
    )
    path_payload = (
        path(snapshot, first_node_id, second_node_id, max_hops=4).to_dict()
        if first_node_id and second_node_id
        else {}
    )
    return InvestigationBundle(
        schema_version=INVESTIGATION_SCHEMA_VERSION,
        boundary="observed_facts_only",
        query=query_text,
        preset=preset,
        health=health(snapshot).to_dict(),
        matches=matches,
        related=_related_payload(snapshot, first_node_id, max_results=max_results),
        neighborhood=neighborhood_payload,
        path=path_payload,
        freshness=_freshness_payload(snapshot, result_payload),
        next_commands=_next_commands(
            snapshot_path=snapshot_path,
            query_text=query_text,
            first_node_id=first_node_id,
            second_node_id=second_node_id,
            preset=preset,
        ),
    )


def render_markdown_investigation(bundle: InvestigationBundle) -> str:
    """Render a compact, public-facing investigation handoff."""
    payload = bundle.to_dict()
    lines = [
        f"# PragmaGraph Investigation: {payload['query']}",
        "",
        f"- Preset: `{payload['preset']}`",
        f"- Boundary: `{payload['boundary']}`",
        f"- Nodes: `{payload['health']['node_count']}`",
        f"- Edges: `{payload['health']['edge_count']}`",
        "",
        "## Matches",
    ]
    if not payload["matches"]:
        lines.append("- No observed matches.")
    for item in payload["matches"]:
        lines.append(
            "- "
            f"`{item['node_id']}` {item['label']} "
            f"({item['kind']}) - {', '.join(item['why']) or 'structural match'}"
        )
    lines.extend(["", "## Next Commands"])
    for name, command in payload["next_commands"].items():
        lines.append(f"- `{name}`: `{' '.join(command)}`")
    return "\n".join(lines) + "\n"


def _preset_nodes(
    snapshot: GraphSnapshot,
    preset: InvestigationPreset,
) -> tuple[GraphNode, ...]:
    if preset == "file_map":
        return _nodes_by_kind(snapshot, {"file"})
    if preset == "symbol_map":
        return _nodes_by_kind(
            snapshot,
            {"python_class", "python_function", "python_module", "symbol"},
        )
    if preset == "doc_links":
        referenced = {
            edge.source_id
            for edge in snapshot.edges
            if edge.kind in {"references_doc", "references_section", "documents"}
        } | {
            edge.target_id
            for edge in snapshot.edges
            if edge.kind in {"references_doc", "references_section", "documents"}
        }
        return tuple(node for node in snapshot.nodes if node.id in referenced)
    if preset == "changed_recently":
        return tuple(
            node
            for node in snapshot.nodes
            if str(node.metadata.get("freshness", "") or "") in {"changed", "fresh"}
            or str(node.metadata.get("committer_time_epoch", "") or "")
        )
    if preset == "orphans":
        connected = {
            node_id
            for edge in snapshot.edges
            for node_id in (edge.source_id, edge.target_id)
        }
        return tuple(node for node in snapshot.nodes if node.id not in connected)
    if preset == "high_degree":
        degree = _degree_map(snapshot.edges)
        return tuple(
            sorted(
                snapshot.nodes,
                key=lambda node: (-degree.get(node.id, 0), node.kind, node.id),
            )
        )
    return snapshot.nodes


def _nodes_by_kind(snapshot: GraphSnapshot, kinds: set[str]) -> tuple[GraphNode, ...]:
    return tuple(node for node in snapshot.nodes if node.kind in kinds)


def _match_payload(hit: Mapping[str, Any]) -> Mapping[str, Any]:
    node = hit.get("node", {})
    explanation = hit.get("explanation", {})
    why = tuple(
        str(item)
        for item in (
            explanation.get("match_summary") or explanation.get("matched_fields") or ()
        )
    )
    return {
        "node_id": str(node.get("id", "") or ""),
        "kind": str(node.get("kind", "") or ""),
        "label": str(node.get("label", "") or ""),
        "source_ref": dict(node.get("source_ref", {}) or {}),
        "score": float(hit.get("score", 0.0) or 0.0),
        "why": why,
        "edge_count": len(hit.get("edges", ()) or ()),
    }


def _node_id(matches: tuple[Mapping[str, Any], ...], index: int) -> str:
    if index >= len(matches):
        return ""
    return str(matches[index].get("node_id", "") or "")


def _related_payload(
    snapshot: GraphSnapshot,
    node_id: str,
    *,
    max_results: int,
) -> Mapping[str, tuple[Mapping[str, Any], ...]]:
    if not node_id:
        return {}
    node_map = snapshot.node_map()
    buckets: dict[str, list[Mapping[str, Any]]] = {
        "files": [],
        "symbols": [],
        "docs": [],
        "other": [],
    }
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        other_id = ""
        if edge.source_id == node_id:
            other_id = edge.target_id
        elif edge.target_id == node_id:
            other_id = edge.source_id
        if not other_id:
            continue
        node = node_map.get(other_id)
        if node is None:
            continue
        bucket = _related_bucket(node)
        if len(buckets[bucket]) >= max_results:
            continue
        buckets[bucket].append(_related_node_payload(node, edge))
    return {key: tuple(value) for key, value in buckets.items() if value}


def _related_node_payload(node: GraphNode, edge: GraphEdge) -> Mapping[str, Any]:
    return {
        "node_id": node.id,
        "kind": node.kind,
        "label": node.label,
        "path": node.source_ref.path,
        "via_edge": edge.kind,
    }


def _related_bucket(node: GraphNode) -> str:
    if node.kind == "file":
        return "files"
    if "doc" in node.kind or node.source_ref.path.endswith(".md"):
        return "docs"
    if "function" in node.kind or "class" in node.kind or "symbol" in node.kind:
        return "symbols"
    return "other"


def _freshness_payload(
    snapshot: GraphSnapshot,
    query_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    return {
        "created_at": snapshot.created_at,
        "indexer_version": snapshot.indexer_version,
        "git_overlay_enabled": bool(snapshot.stats.get("git_overlay_enabled", False)),
        "git_commit_count": int(snapshot.stats.get("git_commit_count", 0) or 0),
        "omitted_count": len(snapshot.omitted),
        "query_page_complete": bool(
            query_payload.get("diagnostics", {}).get("page_complete", True)
        ),
    }


def _next_commands(
    *,
    snapshot_path: str,
    query_text: str,
    first_node_id: str,
    second_node_id: str,
    preset: str,
) -> Mapping[str, tuple[str, ...]]:
    snapshot_arg = snapshot_path or "<snapshot.json>"
    commands: dict[str, tuple[str, ...]] = {
        "query": ("pragmagraph", "query", snapshot_arg, query_text, "--json"),
        "explain": ("pragmagraph", "explain", snapshot_arg, query_text, "--json"),
        "investigate": (
            "pragmagraph",
            "investigate",
            snapshot_arg,
            query_text,
            "--preset",
            preset,
            "--json",
        ),
        "workbench": (
            "pragmagraph",
            "ui-preview",
            "--snapshot",
            snapshot_arg,
            "--query",
            query_text,
            "--screen",
            "search",
            "--serve",
            "--open",
        ),
    }
    if first_node_id:
        commands["neighborhood"] = (
            "pragmagraph",
            "neighborhood",
            snapshot_arg,
            first_node_id,
            "--json",
        )
    if first_node_id and second_node_id:
        commands["path"] = (
            "pragmagraph",
            "path",
            snapshot_arg,
            first_node_id,
            second_node_id,
            "--json",
        )
    return commands


def _degree_map(edges: tuple[GraphEdge, ...]) -> dict[str, int]:
    degree: dict[str, int] = {}
    for edge in edges:
        degree[edge.source_id] = degree.get(edge.source_id, 0) + 1
        degree[edge.target_id] = degree.get(edge.target_id, 0) + 1
    return degree


__all__ = [
    "INVESTIGATION_PRESETS",
    "INVESTIGATION_SCHEMA_VERSION",
    "InvestigationBundle",
    "InvestigationPreset",
    "build_investigation_bundle",
    "render_markdown_investigation",
]
