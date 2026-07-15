"""Deterministic text exports for PragmaGraph snapshots."""

from __future__ import annotations

import re

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot

EXPORT_SCHEMA_VERSION = "pragmagraph.export.v1alpha1"


def _dot_quote(value: object) -> str:
    text = str(value)
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )
    return f'"{escaped}"'


def _mermaid_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace('"', "#quot;")
        .replace("[", "&#91;")
        .replace("]", "&#93;")
        .replace("|", "&#124;")
        .replace("\n", "<br/>")
        .replace("\r", "")
    )


def _mermaid_id(index: int) -> str:
    return f"n{index}"


def _node_label(node: GraphNode) -> str:
    source = node.source_ref.path
    if source and source != node.label:
        return f"{node.label}\\n{node.kind}\\n{source}"
    return f"{node.label}\\n{node.kind}"


def _sorted_nodes(snapshot: GraphSnapshot) -> tuple[GraphNode, ...]:
    return tuple(sorted(snapshot.nodes, key=lambda node: node.id))


def _sorted_edges(snapshot: GraphSnapshot) -> tuple[GraphEdge, ...]:
    return tuple(sorted(snapshot.edges, key=lambda edge: edge.id))


def render_dot(snapshot: GraphSnapshot) -> str:
    """Render ``snapshot`` as deterministic Graphviz DOT."""
    lines = [
        f"// export_schema_version={EXPORT_SCHEMA_VERSION}",
        f"// snapshot_schema_version={snapshot.schema_version}",
        "digraph pragmagraph {",
        "  graph [rankdir=LR];",
        "  node [shape=box];",
    ]
    node_ids = {node.id for node in snapshot.nodes}
    for node in _sorted_nodes(snapshot):
        lines.append(
            "  "
            f"{_dot_quote(node.id)} "
            f"[label={_dot_quote(_node_label(node))}, kind={_dot_quote(node.kind)}];"
        )
    for edge in _sorted_edges(snapshot):
        if edge.source_id not in node_ids or edge.target_id not in node_ids:
            continue
        lines.append(
            "  "
            f"{_dot_quote(edge.source_id)} -> {_dot_quote(edge.target_id)} "
            f"[label={_dot_quote(edge.kind)}, kind={_dot_quote(edge.kind)}];"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_mermaid(snapshot: GraphSnapshot) -> str:
    """Render ``snapshot`` as deterministic Mermaid flowchart text."""
    nodes = _sorted_nodes(snapshot)
    mermaid_ids = {node.id: _mermaid_id(index) for index, node in enumerate(nodes)}
    lines = [
        f"%% export_schema_version={EXPORT_SCHEMA_VERSION}",
        f"%% snapshot_schema_version={snapshot.schema_version}",
        "flowchart LR",
    ]
    for node in nodes:
        lines.append(
            f'  {mermaid_ids[node.id]}["{_mermaid_escape(_node_label(node))}"]'
        )
    for edge in _sorted_edges(snapshot):
        source_id = mermaid_ids.get(edge.source_id)
        target_id = mermaid_ids.get(edge.target_id)
        if source_id is None or target_id is None:
            continue
        label = _mermaid_escape(edge.kind)
        lines.append(f"  {source_id} -->|{label}| {target_id}")
    return "\n".join(lines) + "\n"


def render_graph_export(snapshot: GraphSnapshot, *, format: str) -> str:
    """Render ``snapshot`` in a supported deterministic text export format."""
    normalized = re.sub(r"[-_]", "", format.strip().lower())
    if normalized == "dot":
        return render_dot(snapshot)
    if normalized in {"mermaid", "mmd"}:
        return render_mermaid(snapshot)
    supported = "dot, mermaid"
    raise ValueError(
        f"unsupported graph export format {format!r}; expected {supported}"
    )


from pragmagraph.export.redaction import (  # noqa: E402
    EXPORT_PROFILES,
    EXPORT_PROFILE_FULL,
    EXPORT_PROFILE_NO_CONTENT,
    EXPORT_PROFILE_NO_IDENTITIES,
    EXPORT_PROFILE_PORTABLE,
    ExportProjection,
    project_snapshot,
)


__all__ = [
    "EXPORT_PROFILES",
    "EXPORT_PROFILE_FULL",
    "EXPORT_PROFILE_NO_CONTENT",
    "EXPORT_PROFILE_NO_IDENTITIES",
    "EXPORT_PROFILE_PORTABLE",
    "EXPORT_SCHEMA_VERSION",
    "ExportProjection",
    "project_snapshot",
    "render_dot",
    "render_graph_export",
    "render_mermaid",
]
