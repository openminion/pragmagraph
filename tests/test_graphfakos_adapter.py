from __future__ import annotations

from graphfakos import (
    FileGraphProvider,
    GraphFakosGraphActionProvider,
    GraphFakosRequest,
    render_static_html,
)
from graphfakos.artifacts import write_graph_artifact
from graphfakos.provider import load_provider_graph
import pytest

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.ui.graphfakos_adapter import (
    PragmaGraphLiveViewerProvider,
    PragmaGraphViewerProvider,
)


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
    graphfakos_conformance = pytest.importorskip("graphfakos.testing.conformance")
    result = graphfakos_conformance.assert_provider_conformance(
        graphfakos_conformance.GraphFakosProviderConformanceCase(
            provider=provider,
            request=GraphFakosRequest(),
            expected_role="source",
            expected_provider="PragmaGraph",
            expected_node="README.md",
            expected_edge="documents",
            required_capabilities=(
                "search",
                "neighborhood",
                "path",
                "provenance",
                "provider_status",
                "static_export",
                "local_preview",
            ),
        )
    )
    graph = result.graph

    assert graph.provider_id == "pragmagraph"
    assert graph.graph_role == "source"
    assert any(node.label == "README.md" for node in graph.nodes)
    assert any(edge.kind == "documents" for edge in graph.edges)
    assert graph.citations
    assert graph.provider_payload["namespace"] == "demo"
    assert "integration_commands" in graph.provider_payload
    assert graph.provider_payload["project_health"] == {
        "created_at": "2026-06-22T00:00:00+00:00",
        "edge_count": 1,
        "edge_kinds": {"documents": 1},
        "node_count": 2,
        "node_kinds": {"file": 1, "python_function": 1},
        "omitted_count": 0,
        "omitted_reasons": {},
        "parser_set": ["python_ast"],
        "source_path_count": 2,
    }


def test_pragmagraph_adapter_artifact_round_trip_matches_loaded_graph(tmp_path) -> None:
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
            ),
        ),
        edges=(),
        stats={"parser_set": ("python_ast",)},
        created_at="2026-06-22T00:00:00+00:00",
    )
    provider = PragmaGraphViewerProvider(snapshot)
    request = GraphFakosRequest(screen="provider_status")
    graph = load_provider_graph(provider, request)
    artifact_path = tmp_path / "pragmagraph-artifact.json"
    write_graph_artifact(graph, str(artifact_path))
    replay_provider = FileGraphProvider(str(artifact_path))
    replay_graph = load_provider_graph(replay_provider, request)
    replay_html = render_static_html(replay_provider, request)

    assert replay_graph.to_dict() == graph.to_dict()
    assert "PragmaGraph Observed Source Graph" in replay_html
    assert "README.md" in replay_html


def test_pragmagraph_live_adapter_emits_structural_snapshot_patch() -> None:
    graphfakos_live = pytest.importorskip("graphfakos.live")
    graphfakos_assertions = pytest.importorskip("graphfakos.testing.assertions")
    initial = GraphSnapshot(
        namespace="demo",
        root_path="repo",
        nodes=(
            GraphNode(
                id="file:README.md",
                kind="file",
                label="README.md",
                source_ref=SourceRef(path="README.md", line=1),
                text="Repository overview.",
            ),
        ),
        edges=(),
        created_at="2026-07-12T00:00:00Z",
    )
    updated = GraphSnapshot(
        namespace="demo",
        root_path="repo",
        nodes=(
            *initial.nodes,
            GraphNode(
                id="symbol:build",
                kind="python_function",
                label="build",
                source_ref=SourceRef(path="src/app.py", line=3),
                text="Build the graph.",
            ),
        ),
        edges=(
            GraphEdge(
                id="edge:documents",
                kind="documents",
                source_id="file:README.md",
                target_id="symbol:build",
            ),
        ),
        created_at="2026-07-12T00:01:00Z",
    )
    live_provider = PragmaGraphLiveViewerProvider(initial, (updated,))

    assert not isinstance(live_provider, GraphFakosGraphActionProvider)

    state = graphfakos_assertions.assert_live_provider_contract(
        live_provider,
        initial_graph=live_provider.load_graph(GraphFakosRequest()),
        initial_revision="0",
        request=graphfakos_live.GraphFakosLiveSessionRequest(
            session_id="pragmagraph-test"
        ),
    )

    assert set(state.graph.node_map()) == {"file:README.md", "symbol:build"}
    assert set(state.graph.edge_map()) == {"edge:documents"}
    assert state.graph.provider_id == "pragmagraph"
