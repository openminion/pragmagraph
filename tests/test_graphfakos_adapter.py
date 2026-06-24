from __future__ import annotations

from graphfakos import GraphFakosRequest, render_static_html
from graphfakos.testing import assert_graph_viewer_contract

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.ui.graphfakos_adapter import PragmaGraphViewerProvider


def test_pragmagraph_adapter_returns_third_brain_graphfakos_graph() -> None:
    snapshot = GraphSnapshot(
        namespace="demo",
        root_path="repo",
        nodes=(
            GraphNode(
                id="file:README.md",
                kind="file",
                label="README.md",
                source_ref=SourceRef(path="README.md", line=1),
                text="Repository overview.",
                metadata={"freshness": "fresh"},
            ),
            GraphNode(
                id="symbol:build_graph",
                kind="python_function",
                label="build_graph",
                source_ref=SourceRef(path="src/app.py", line=12),
                text="Builds graph facts.",
            ),
        ),
        edges=(
            GraphEdge(
                id="edge:readme-docs-symbol",
                kind="documents",
                source_id="file:README.md",
                target_id="symbol:build_graph",
            ),
        ),
        stats={"parser_set": ("python_ast",)},
        created_at="2026-06-22T00:00:00+00:00",
    )
    provider = PragmaGraphViewerProvider(snapshot)
    graph = provider.load_graph(GraphFakosRequest())
    html = render_static_html(provider, GraphFakosRequest())

    assert graph.provider_id == "pragmagraph"
    assert graph.graph_role == "source"
    assert any(node.label == "README.md" for node in graph.nodes)
    assert any(edge.kind == "documents" for edge in graph.edges)
    assert graph.citations
    assert graph.provider_payload["namespace"] == "demo"
    assert "integration_commands" in graph.provider_payload
    assert_graph_viewer_contract(
        html,
        expected_role="source",
        expected_provider="PragmaGraph",
        expected_node="README.md",
        expected_edge="documents",
    )
