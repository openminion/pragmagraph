"""Local visual preview helpers for the package-owned PragmaGraph UI."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal
import webbrowser

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, QueryRequest, SourceRef
from pragmagraph.query import health, neighborhood, path as graph_path, query as graph_query
from pragmagraph.storage import load_snapshot
from pragmagraph.workspace import load_workspace_metadata

from .contracts import build_ui_screen_manifest
from .local_server import (
    LocalVisualHttpServer,
    LocalVisualServerResult,
    make_local_visual_server,
    serve_local_visual_server,
)

PreviewScreen = Literal[
    "search",
    "result_detail",
    "neighborhood",
    "path",
    "provider_status",
]


@dataclass(frozen=True, slots=True)
class UiPreviewRequest:
    """Request for rendering or serving the local PragmaGraph visual UI."""

    screen: PreviewScreen = "search"
    workspace: str | None = None
    snapshot: str | None = None
    output_path: str = "pragmagraph-ui-preview.html"
    query: str = "RuntimeGraph"
    node_id: str | None = None
    source_id: str | None = None
    target_id: str | None = None
    open_browser: bool = False


@dataclass(frozen=True, slots=True)
class UiPreviewResult:
    """File-render result for the local visual preview."""

    output_path: str
    screen: str
    workspace: str | None
    snapshot: str | None
    node_count: int
    edge_count: int
    opened: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": self.output_path,
            "screen": self.screen,
            "workspace": self.workspace,
            "snapshot": self.snapshot,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "opened": self.opened,
        }


@dataclass(frozen=True, slots=True)
class UiPreviewRender:
    """HTML render result for the local visual preview."""

    html: str
    screen: str
    workspace: str | None
    snapshot: str | None
    node_count: int
    edge_count: int


def write_ui_preview(request: UiPreviewRequest) -> UiPreviewResult:
    """Write one local visual UI preview to an HTML file."""
    rendered = render_ui_preview(request)
    output_path = Path(request.output_path).expanduser().resolve(strict=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.html, encoding="utf-8")
    opened = False
    if request.open_browser:
        opened = webbrowser.open(output_path.as_uri())
    return UiPreviewResult(
        output_path=str(output_path),
        screen=rendered.screen,
        workspace=rendered.workspace,
        snapshot=rendered.snapshot,
        node_count=rendered.node_count,
        edge_count=rendered.edge_count,
        opened=opened,
    )


def render_ui_preview(request: UiPreviewRequest) -> UiPreviewRender:
    """Render the local visual UI preview for a snapshot, workspace, or demo graph."""
    snapshot = _snapshot_for_request(request)
    html = _render_page(snapshot, request)
    return UiPreviewRender(
        html=html,
        screen=request.screen,
        workspace=request.workspace,
        snapshot=request.snapshot,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
    )


def make_ui_preview_server(
    request: UiPreviewRequest,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
) -> LocalVisualHttpServer:
    """Create a local visual UI server without starting its event loop."""
    return make_local_visual_server(
        render_path=lambda path, query: _render_server_path(request, path, query),
        default_path=f"/{request.screen}",
        host=host,
        port=port,
    )


def serve_ui_preview(
    request: UiPreviewRequest,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
) -> LocalVisualServerResult:
    """Serve the local visual UI until interrupted."""
    return serve_local_visual_server(
        render_path=lambda path, query: _render_server_path(request, path, query),
        default_path=f"/{request.screen}",
        host=host,
        port=port,
        open_browser=request.open_browser,
    )


def _render_server_path(
    request: UiPreviewRequest,
    path: str,
    query: dict[str, list[str]],
) -> str:
    screen = _screen_from_path(path) or request.screen
    return render_ui_preview(
        _request_from_query(request, screen=screen, query=query)
    ).html


def _request_from_query(
    request: UiPreviewRequest,
    *,
    screen: PreviewScreen,
    query: dict[str, list[str]],
) -> UiPreviewRequest:
    return UiPreviewRequest(
        screen=screen,
        workspace=_first_query_value(query, "workspace") or request.workspace,
        snapshot=_first_query_value(query, "snapshot") or request.snapshot,
        output_path=request.output_path,
        query=_first_query_value(query, "query") or request.query,
        node_id=_first_query_value(query, "node_id") or request.node_id,
        source_id=_first_query_value(query, "source_id") or request.source_id,
        target_id=_first_query_value(query, "target_id") or request.target_id,
        open_browser=False,
    )


def _first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values and values[0] else None


def _screen_from_path(path: str) -> PreviewScreen | None:
    value = path.strip("/") or "search"
    aliases = {
        "": "search",
        "result": "result_detail",
        "providers": "provider_status",
        "status": "provider_status",
    }
    value = aliases.get(value, value)
    if value in {"search", "result_detail", "neighborhood", "path", "provider_status"}:
        return value  # type: ignore[return-value]
    return None


def _snapshot_for_request(request: UiPreviewRequest) -> GraphSnapshot:
    if request.workspace:
        metadata = load_workspace_metadata(request.workspace)
        return load_snapshot(metadata.paths.snapshot_path)
    if request.snapshot:
        return load_snapshot(request.snapshot)
    return _demo_snapshot()


def _render_page(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    active = request.screen
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>PragmaGraph UI</title>"
        f"{_STYLE}</head><body class='pg-page'><div class='pg-shell'>"
        f"{_render_nav(active)}"
        "<main class='pg-content'>"
        f"{_render_header(snapshot, request)}"
        f"{_render_screen(snapshot, request)}"
        "</main></div></body></html>"
    )


def _render_nav(active: str) -> str:
    items = (
        ("search", "Search"),
        ("result_detail", "Result"),
        ("neighborhood", "Neighborhood"),
        ("path", "Path"),
        ("provider_status", "Providers"),
    )
    links = ""
    for screen, label in items:
        current = 'aria-current="page"' if active == screen else ""
        links += f"<a href='/{screen}' {current}>{label}</a>"
    return f"<nav class='pg-nav'><h1>PragmaGraph</h1>{links}</nav>"


def _render_header(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    title = dict(_screen_titles()).get(request.screen, "PragmaGraph")
    root = snapshot.root_path or "demo workspace"
    return (
        "<header class='pg-header'>"
        "<div><p class='pg-eyebrow'>Observed fact graph</p>"
        f"<h2>{escape(title)}</h2>"
        f"<p>{escape(root)}</p></div>"
        "<div class='pg-summary'>"
        f"{_badge(f'{len(snapshot.nodes)} nodes', 'accent')}"
        f"{_badge(f'{len(snapshot.edges)} edges', 'blue')}"
        f"{_badge(snapshot.namespace, 'neutral')}"
        "</div></header>"
    )


def _screen_titles() -> tuple[tuple[str, str], ...]:
    return (
        ("search", "Search"),
        ("result_detail", "Result Detail"),
        ("neighborhood", "Neighborhood"),
        ("path", "Path Explorer"),
        ("provider_status", "Provider Status"),
    )


def _render_screen(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    if request.screen == "result_detail":
        return _render_result_detail(snapshot, request)
    if request.screen == "neighborhood":
        return _render_neighborhood(snapshot, request)
    if request.screen == "path":
        return _render_path(snapshot, request)
    if request.screen == "provider_status":
        return _render_provider_status(snapshot)
    return _render_search(snapshot, request)


def _render_search(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    result = graph_query(
        snapshot,
        QueryRequest(query=request.query, max_results=8, include_edges=True),
    )
    hits = "".join(_render_hit(hit.node, hit.score, hit.snippet) for hit in result.hits)
    return (
        "<section class='pg-toolbar'>"
        "<form method='get' action='/search'>"
        f"<input name='query' value='{escape(request.query)}' "
        "placeholder='Search files, symbols, docs, dependencies'>"
        "<button type='submit'>Search</button></form></section>"
        "<section class='pg-layout'><div class='pg-panel'>"
        "<h3>Ranked Results</h3>"
        f"{hits or _empty('No matching observed facts.')}"
        "</div><aside class='pg-panel'>"
        "<h3>Query Diagnostics</h3>"
        f"{_key_values(result.diagnostics)}"
        "<h3>Omitted</h3>"
        f"{_omitted_list(snapshot)}"
        "</aside></section>"
    )


def _render_result_detail(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    node = _selected_node(snapshot, request)
    if node is None:
        return _panel("Result Detail", _empty("No nodes are available."))
    edges = _incident_edges(snapshot, node.id)
    return (
        "<section class='pg-layout'><div class='pg-panel'>"
        f"<h3>{escape(node.label)}</h3>"
        f"{_badge(node.kind, 'accent')}"
        f"<p>{escape(node.text or node.source_ref.path or node.id)}</p>"
        f"{_key_values(node.metadata)}"
        "</div><aside class='pg-panel'>"
        "<h3>Source</h3>"
        f"{_source_ref(node.source_ref)}"
        "<h3>Incident Edges</h3>"
        f"{_edge_list(edges)}"
        "</aside></section>"
    )


def _render_neighborhood(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    node = _selected_node(snapshot, request)
    if node is None:
        return _panel("Neighborhood", _empty("No nodes are available."))
    result = neighborhood(snapshot, node.id, depth=1, max_results=12)
    hits = "".join(_render_hit(hit.node, hit.score, hit.snippet) for hit in result.hits)
    return (
        "<section class='pg-layout'><div class='pg-panel'>"
        f"<h3>Around {escape(node.label)}</h3>"
        f"{hits or _empty('No neighboring observed facts.')}"
        "</div><aside class='pg-panel'>"
        "<h3>Center Node</h3>"
        f"{_node_link(node)}"
        "<h3>Edges</h3>"
        f"{_edge_list(_incident_edges(snapshot, node.id))}"
        "</aside></section>"
    )


def _render_path(snapshot: GraphSnapshot, request: UiPreviewRequest) -> str:
    source, target = _path_nodes(snapshot, request)
    if source is None or target is None:
        return _panel("Path Explorer", _empty("At least two nodes are required."))
    result = graph_path(snapshot, source.id, target.id, max_hops=4)
    nodes = "".join(_render_compact_node(node) for node in result.nodes)
    edges = _edge_list(result.edges)
    return (
        "<section class='pg-layout'><div class='pg-panel'>"
        f"<h3>{escape(source.label)} to {escape(target.label)}</h3>"
        f"{nodes or _empty('No bounded path found.')}"
        "</div><aside class='pg-panel'>"
        "<h3>Path Edges</h3>"
        f"{edges}"
        "</aside></section>"
    )


def _render_provider_status(snapshot: GraphSnapshot) -> str:
    summary = health(snapshot)
    screens = "".join(
        "<li>"
        f"<strong>{escape(screen.title)}</strong>"
        f"<span>{escape(screen.route)}</span>"
        "</li>"
        for screen in build_ui_screen_manifest()
    )
    return (
        "<section class='pg-layout'><div class='pg-panel'>"
        "<h3>Snapshot Health</h3>"
        f"{_key_values(summary.to_dict())}"
        "</div><aside class='pg-panel'>"
        "<h3>Aligned Screens</h3>"
        f"<ul class='pg-list'>{screens}</ul>"
        "</aside></section>"
    )


def _render_hit(node: GraphNode, score: float, snippet: str) -> str:
    return (
        "<article class='pg-card'>"
        f"<div>{_badge(node.kind, 'accent')}{_badge(f'{score:.0f}', 'blue')}</div>"
        f"<h4>{_node_link(node)}</h4>"
        f"<p>{escape(snippet)}</p>"
        f"<small>{escape(node.source_ref.path or node.id)}</small>"
        "</article>"
    )


def _render_compact_node(node: GraphNode) -> str:
    return (
        "<article class='pg-card pg-compact'>"
        f"{_badge(node.kind, 'accent')}"
        f"<strong>{_node_link(node)}</strong>"
        f"<span>{escape(node.source_ref.path or node.id)}</span>"
        "</article>"
    )


def _node_link(node: GraphNode) -> str:
    return (
        f"<a href='/result_detail?node_id={escape(node.id)}'>"
        f"{escape(node.label)}</a>"
    )


def _selected_node(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> GraphNode | None:
    node_map = snapshot.node_map()
    if request.node_id and request.node_id in node_map:
        return node_map[request.node_id]
    result = graph_query(snapshot, QueryRequest(query=request.query, max_results=1))
    if result.hits:
        return result.hits[0].node
    return snapshot.nodes[0] if snapshot.nodes else None


def _path_nodes(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> tuple[GraphNode | None, GraphNode | None]:
    node_map = snapshot.node_map()
    source = node_map.get(request.source_id or "") if request.source_id else None
    target = node_map.get(request.target_id or "") if request.target_id else None
    if source is not None and target is not None:
        return source, target
    if len(snapshot.nodes) < 2:
        return None, None
    return snapshot.nodes[0], snapshot.nodes[-1]


def _incident_edges(snapshot: GraphSnapshot, node_id: str) -> tuple[GraphEdge, ...]:
    return tuple(
        edge
        for edge in snapshot.edges
        if edge.source_id == node_id or edge.target_id == node_id
    )


def _edge_list(edges: tuple[GraphEdge, ...]) -> str:
    if not edges:
        return _empty("No edges.")
    return "<ul class='pg-list'>" + "".join(
        "<li>"
        f"{_badge(edge.kind, 'blue')}"
        f"<span>{escape(edge.source_id)} -> {escape(edge.target_id)}</span>"
        "</li>"
        for edge in edges
    ) + "</ul>"


def _omitted_list(snapshot: GraphSnapshot) -> str:
    if not snapshot.omitted:
        return _empty("No omitted facts.")
    return "<ul class='pg-list'>" + "".join(
        f"<li>{escape(item.reason)} {escape(item.item_id)}</li>"
        for item in snapshot.omitted
    ) + "</ul>"


def _key_values(payload: object) -> str:
    if not isinstance(payload, dict):
        return f"<pre>{escape(str(payload))}</pre>"
    rows = "".join(
        "<dt>" + escape(str(key)) + "</dt>"
        "<dd>" + escape(str(value)) + "</dd>"
        for key, value in payload.items()
    )
    return f"<dl class='pg-kv'>{rows}</dl>"


def _source_ref(source: SourceRef) -> str:
    return _key_values(source.to_dict())


def _panel(title: str, body: str) -> str:
    return f"<section class='pg-panel'><h3>{escape(title)}</h3>{body}</section>"


def _empty(text: str) -> str:
    return f"<p class='pg-empty'>{escape(text)}</p>"


def _badge(text: str, tone: str) -> str:
    return f"<span class='pg-badge' data-tone='{tone}'>{escape(text)}</span>"


def _demo_snapshot() -> GraphSnapshot:
    nodes = (
        GraphNode(
            id="file:README.md",
            kind="file",
            label="README.md",
            source_ref=SourceRef(path="README.md", line=1),
            text="RuntimeGraph overview and installation notes.",
        ),
        GraphNode(
            id="module:src/runtime_graph.py",
            kind="python_module",
            label="runtime_graph",
            source_ref=SourceRef(path="src/runtime_graph.py", line=1),
            text="Builds observed graph snapshots for local projects.",
        ),
        GraphNode(
            id="symbol:build_runtime_graph",
            kind="python_function",
            label="build_runtime_graph",
            source_ref=SourceRef(path="src/runtime_graph.py", line=12),
            text="Creates a deterministic PragmaGraph snapshot.",
            metadata={"signature": "build_runtime_graph(root)"},
        ),
        GraphNode(
            id="dependency:tree-sitter",
            kind="dependency",
            label="tree-sitter",
            source_ref=SourceRef(path="pyproject.toml", section="dependencies"),
            text="Optional precise parser dependency.",
        ),
    )
    edges = (
        GraphEdge(
            id="edge:readme-docs-module",
            kind="documents",
            source_id="file:README.md",
            target_id="module:src/runtime_graph.py",
        ),
        GraphEdge(
            id="edge:module-defines-symbol",
            kind="defines",
            source_id="module:src/runtime_graph.py",
            target_id="symbol:build_runtime_graph",
        ),
        GraphEdge(
            id="edge:module-uses-parser",
            kind="uses_optional_dependency",
            source_id="module:src/runtime_graph.py",
            target_id="dependency:tree-sitter",
        ),
    )
    return GraphSnapshot(
        namespace="demo",
        root_path="demo/pragmagraph-workspace",
        nodes=nodes,
        edges=edges,
        stats={"parser_set": ("python_ast", "markdown", "config")},
        created_at="2026-06-21T00:00:00+00:00",
    )


_STYLE = """
<style>
:root {
  color-scheme: light;
  --pg-bg: #f7f7f4;
  --pg-ink: #17211d;
  --pg-muted: #65716c;
  --pg-line: #d9ded8;
  --pg-panel: #ffffff;
  --pg-soft: #eef2ef;
  --pg-accent: #216b61;
  --pg-accent-soft: #dff0ec;
  --pg-blue: #325c8f;
  --pg-blue-soft: #e0e9f6;
}
* { box-sizing: border-box; }
body.pg-page {
  margin: 0;
  background: var(--pg-bg);
  color: var(--pg-ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.45;
}
.pg-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
}
.pg-nav {
  border-right: 1px solid var(--pg-line);
  background: #fbfcfa;
  padding: 20px 14px;
}
.pg-nav h1 {
  margin: 0 0 18px;
  font-size: 18px;
}
.pg-nav a {
  display: flex;
  align-items: center;
  min-height: 36px;
  margin: 4px 0;
  padding: 8px 10px;
  border-radius: 8px;
  color: var(--pg-muted);
  text-decoration: none;
  font-size: 14px;
}
.pg-nav a[aria-current="page"] {
  background: var(--pg-accent-soft);
  color: var(--pg-accent);
  font-weight: 700;
}
.pg-content {
  min-width: 0;
  padding: 24px;
}
.pg-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
  margin-bottom: 18px;
}
.pg-eyebrow {
  margin: 0 0 4px;
  color: var(--pg-muted);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
.pg-header h2 {
  margin: 0;
  font-size: 30px;
  line-height: 1.1;
}
.pg-header p {
  margin: 8px 0 0;
  color: var(--pg-muted);
}
.pg-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.pg-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, .8fr);
  gap: 16px;
  align-items: start;
}
.pg-panel {
  background: var(--pg-panel);
  border: 1px solid var(--pg-line);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.pg-panel h3 {
  margin: 0 0 12px;
  font-size: 16px;
}
.pg-toolbar {
  margin-bottom: 16px;
}
.pg-toolbar form {
  display: flex;
  gap: 8px;
}
.pg-toolbar input {
  min-width: 0;
  flex: 1;
  border: 1px solid var(--pg-line);
  border-radius: 8px;
  padding: 10px 12px;
  font: inherit;
}
.pg-toolbar button {
  border: 1px solid var(--pg-accent);
  border-radius: 8px;
  background: var(--pg-accent);
  color: white;
  padding: 10px 14px;
  font: inherit;
  font-weight: 700;
}
.pg-card {
  border: 1px solid var(--pg-line);
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  margin-bottom: 10px;
  overflow-wrap: anywhere;
}
.pg-card h4 {
  margin: 8px 0;
  font-size: 15px;
}
.pg-card p {
  margin: 8px 0;
}
.pg-card small,
.pg-compact span {
  color: var(--pg-muted);
}
.pg-compact {
  display: grid;
  gap: 6px;
}
.pg-badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  margin: 0 6px 6px 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--pg-soft);
  color: var(--pg-muted);
  font-size: 12px;
  font-weight: 700;
}
.pg-badge[data-tone="accent"] {
  background: var(--pg-accent-soft);
  color: var(--pg-accent);
}
.pg-badge[data-tone="blue"] {
  background: var(--pg-blue-soft);
  color: var(--pg-blue);
}
.pg-list {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}
.pg-list li {
  border: 1px solid var(--pg-line);
  border-radius: 8px;
  padding: 9px 10px;
  background: #fff;
  overflow-wrap: anywhere;
}
.pg-list li span {
  display: block;
  color: var(--pg-muted);
  font-size: 13px;
}
.pg-kv {
  display: grid;
  grid-template-columns: minmax(100px, .45fr) minmax(0, 1fr);
  gap: 8px 12px;
  margin: 0;
}
.pg-kv dt {
  color: var(--pg-muted);
  font-size: 13px;
}
.pg-kv dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.pg-empty {
  margin: 0;
  color: var(--pg-muted);
}
a {
  color: var(--pg-accent);
  text-decoration: none;
}
@media (max-width: 760px) {
  .pg-shell { grid-template-columns: 1fr; }
  .pg-nav { border-right: 0; border-bottom: 1px solid var(--pg-line); }
  .pg-layout,
  .pg-header { grid-template-columns: 1fr; }
  .pg-summary { justify-content: flex-start; }
}
</style>
"""


__all__ = [
    "PreviewScreen",
    "UiPreviewRender",
    "UiPreviewRequest",
    "UiPreviewResult",
    "make_ui_preview_server",
    "render_ui_preview",
    "serve_ui_preview",
    "write_ui_preview",
]
