"""GraphFakos adapter for PragmaGraph source graph previews."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphfakos import (
    GraphFakosCitation,
    GraphFakosEdge,
    GraphFakosGraph,
    GraphFakosNode,
    GraphFakosProvenance,
    GraphFakosProvider,
    GraphFakosRequest,
)

from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef

if TYPE_CHECKING:
    from graphfakos.live import (
        GraphFakosGraphPatch,
        GraphFakosLiveSessionDiagnostics,
        GraphFakosLiveSessionRequest,
        GraphFakosLiveSessionStatus,
    )


class PragmaGraphViewerProvider(GraphFakosProvider):
    provider_id = "pragmagraph"
    provider_label = "PragmaGraph"
    graph_role = "source"
    capabilities = (
        "search",
        "neighborhood",
        "path",
        "provenance",
        "freshness",
        "provider_status",
        "project_health",
        "context_preview",
        "source_graph",
        "document_graph",
        "code_graph",
        "artifact_graph",
        "static_export",
        "local_preview",
    )

    def __init__(
        self,
        snapshot: GraphSnapshot,
        project_health_context: dict[str, object] | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._project_health_context = project_health_context

    def load_graph(self, request: GraphFakosRequest) -> GraphFakosGraph:
        return _snapshot_to_graphfakos(
            self._snapshot,
            request,
            provider_id=self.provider_id,
            provider_label=self.provider_label,
            graph_role=self.graph_role,
            capabilities=self.capabilities,
            project_health_context=self._project_health_context,
        )


class PragmaGraphLiveViewerProvider(PragmaGraphViewerProvider):
    """Expose caller-supplied PragmaGraph snapshots as structural live patches."""

    capabilities = (*PragmaGraphViewerProvider.capabilities, "live")

    def __init__(
        self,
        snapshot: GraphSnapshot,
        updates: tuple[GraphSnapshot, ...],
    ) -> None:
        super().__init__(snapshot)
        try:
            from graphfakos.live import (
                GraphFakosGraphRevision,
                InMemoryGraphFakosLiveProvider,
            )
        except ImportError as exc:
            raise RuntimeError(
                "PragmaGraph live viewing requires GraphFakos live-session support"
            ) from exc
        self._live = InMemoryGraphFakosLiveProvider(
            revision=GraphFakosGraphRevision("0")
        )
        previous = _snapshot_to_graphfakos(
            snapshot,
            GraphFakosRequest(),
            provider_id=self.provider_id,
            provider_label=self.provider_label,
            graph_role=self.graph_role,
            capabilities=self.capabilities,
        )
        for index, update in enumerate(updates, start=1):
            current = _snapshot_to_graphfakos(
                update,
                GraphFakosRequest(),
                provider_id=self.provider_id,
                provider_label=self.provider_label,
                graph_role=self.graph_role,
                capabilities=self.capabilities,
            )
            self._live.publish_patch(_snapshot_patch(previous, current, index=index))
            previous = current

    def open_live_session(
        self, request: GraphFakosLiveSessionRequest
    ) -> GraphFakosLiveSessionStatus:
        return self._live.open_live_session(request)

    def load_patch(
        self, request: GraphFakosLiveSessionRequest
    ) -> GraphFakosGraphPatch | GraphFakosLiveSessionStatus:
        return self._live.load_patch(request)

    def diagnostics(self) -> GraphFakosLiveSessionDiagnostics:
        return self._live.diagnostics()


def _snapshot_patch(
    previous: GraphFakosGraph,
    current: GraphFakosGraph,
    *,
    index: int,
) -> GraphFakosGraphPatch:
    from graphfakos.live import (
        GraphFakosGraphPatch,
        GraphFakosGraphRevision,
        GraphFakosLiveSessionCursor,
        GraphFakosPatchOperation,
    )

    previous_nodes = previous.node_map()
    current_nodes = current.node_map()
    previous_edges = previous.edge_map()
    current_edges = current.edge_map()
    operations: list[GraphFakosPatchOperation] = []
    operations.extend(
        GraphFakosPatchOperation(kind="edge_delete", target_id=edge_id)
        for edge_id in sorted(previous_edges.keys() - current_edges.keys())
    )
    operations.extend(
        GraphFakosPatchOperation(kind="node_delete", target_id=node_id)
        for node_id in sorted(previous_nodes.keys() - current_nodes.keys())
    )
    operations.extend(
        GraphFakosPatchOperation(kind="node_upsert", node=current_nodes[node_id])
        for node_id in sorted(current_nodes)
        if current_nodes[node_id] != previous_nodes.get(node_id)
    )
    operations.extend(
        GraphFakosPatchOperation(kind="edge_upsert", edge=current_edges[edge_id])
        for edge_id in sorted(current_edges)
        if current_edges[edge_id] != previous_edges.get(edge_id)
    )
    if previous.provider_payload != current.provider_payload:
        operations.append(
            GraphFakosPatchOperation(
                kind="graph_metadata_replace",
                metadata=current.provider_payload,
            )
        )
    if not operations:
        operations.append(
            GraphFakosPatchOperation(
                kind="graph_metadata_merge",
                metadata={"snapshot_unchanged": True},
            )
        )
    return GraphFakosGraphPatch(
        patch_id=f"pragmagraph:{index}",
        base_revision=GraphFakosGraphRevision(str(index - 1)),
        result_revision=GraphFakosGraphRevision(str(index)),
        cursor=GraphFakosLiveSessionCursor(f"pragmagraph:{index}"),
        operations=tuple(operations),
        occurred_at=current.generated_at,
    )


def _snapshot_to_graphfakos(
    snapshot: GraphSnapshot,
    request: GraphFakosRequest,
    *,
    provider_id: str,
    provider_label: str,
    graph_role: str,
    capabilities: tuple[str, ...],
    project_health_context: dict[str, object] | None = None,
) -> GraphFakosGraph:
    citations = tuple(_citation_for_node(node) for node in snapshot.nodes) + tuple(
        _citation_for_edge(edge) for edge in snapshot.edges
    )
    provenance = tuple(_provenance_for_node(node) for node in snapshot.nodes)
    nodes = tuple(_node_to_graphfakos(node) for node in snapshot.nodes)
    edges = tuple(_edge_to_graphfakos(edge) for edge in snapshot.edges)
    return GraphFakosGraph(
        graph_id=snapshot.namespace,
        label="PragmaGraph Observed Source Graph",
        provider_id=provider_id,
        provider_label=provider_label,
        graph_role=graph_role,
        capabilities=capabilities,
        nodes=nodes,
        edges=edges,
        provenance=provenance,
        citations=citations,
        warnings=tuple(item.reason for item in snapshot.omitted),
        stats={
            "namespace": snapshot.namespace,
            "root_path": snapshot.root_path,
            "request_screen": request.screen,
            **dict(snapshot.stats),
        },
        generated_at=snapshot.created_at,
        provider_payload={
            "namespace": snapshot.namespace,
            "root_path": snapshot.root_path,
            "schema_version": snapshot.schema_version,
            "indexer_version": snapshot.indexer_version,
            "project_health": _project_health_payload(
                snapshot,
                project_health_context=project_health_context,
            ),
            "snapshot_label": (
                f"{snapshot.namespace} snapshot at "
                f"{snapshot.created_at or 'unknown time'}"
            ),
            "integration_commands": (
                "pragmagraph-ui --workspace .pragmagraph-workspace --screen search --serve --open",
                "pragmagraph-ui --workspace .pragmagraph-workspace --screen provider_status --serve",
            ),
        },
    )


def _project_health_payload(
    snapshot: GraphSnapshot,
    *,
    project_health_context: dict[str, object] | None = None,
) -> dict[str, object]:
    paths = {
        item.source_ref.path
        for item in (*snapshot.nodes, *snapshot.edges)
        if item.source_ref.path
    }
    parser_set = snapshot.stats.get("parser_set", ())
    if isinstance(parser_set, str):
        parsers = (parser_set,)
    else:
        parsers = tuple(str(item) for item in parser_set)
    omitted_reasons: dict[str, int] = {}
    for item in snapshot.omitted:
        omitted_reasons[item.reason] = omitted_reasons.get(item.reason, 0) + 1
    payload: dict[str, object] = {
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "omitted_count": len(snapshot.omitted),
        "source_path_count": len(paths),
        "node_kinds": _count_by([node.kind for node in snapshot.nodes]),
        "edge_kinds": _count_by([edge.kind for edge in snapshot.edges]),
        "omitted_reasons": dict(sorted(omitted_reasons.items())),
        "parser_set": sorted(parsers),
        "created_at": snapshot.created_at,
    }
    if project_health_context:
        payload.update(project_health_context)
    return payload


def _count_by(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _node_to_graphfakos(node: GraphNode) -> GraphFakosNode:
    return GraphFakosNode(
        id=node.id,
        label=node.label,
        kind=node.kind,
        summary=node.text or node.source_ref.path or node.id,
        tags=_node_tags(node),
        source=node.source_ref.path,
        timestamps=_timestamps(node.metadata),
        provenance_ids=(f"provenance:{node.id}",),
        citation_ids=(f"citation:node:{node.id}",),
        provider_payload={
            "source_ref": node.source_ref.to_dict(),
            "metadata": dict(node.metadata),
        },
    )


def _edge_to_graphfakos(edge: GraphEdge) -> GraphFakosEdge:
    return GraphFakosEdge(
        id=edge.id,
        source_id=edge.source_id,
        target_id=edge.target_id,
        kind=edge.kind,
        label=edge.kind,
        provenance_ids=(),
        citation_ids=(f"citation:edge:{edge.id}",),
        provider_payload={
            "source_ref": edge.source_ref.to_dict(),
            "metadata": dict(edge.metadata),
        },
    )


def _citation_for_node(node: GraphNode) -> GraphFakosCitation:
    return _citation(
        citation_id=f"citation:node:{node.id}",
        label=node.label,
        source_ref=node.source_ref,
        excerpt=node.text,
    )


def _citation_for_edge(edge: GraphEdge) -> GraphFakosCitation:
    return _citation(
        citation_id=f"citation:edge:{edge.id}",
        label=edge.kind,
        source_ref=edge.source_ref,
        excerpt=f"{edge.source_id} -> {edge.target_id}",
    )


def _citation(
    *,
    citation_id: str,
    label: str,
    source_ref: SourceRef,
    excerpt: str,
) -> GraphFakosCitation:
    return GraphFakosCitation(
        id=citation_id,
        label=label,
        uri=source_ref.uri,
        path=source_ref.path,
        line=source_ref.line,
        span=_source_span(source_ref),
        excerpt=excerpt or source_ref.path or label,
    )


def _provenance_for_node(node: GraphNode) -> GraphFakosProvenance:
    return GraphFakosProvenance(
        id=f"provenance:{node.id}",
        provider_id="pragmagraph",
        source_type=node.kind,
        source_label=node.source_ref.path or node.label,
        source_uri=node.source_ref.uri,
        excerpt=node.text or node.label,
        observed_at=str(node.metadata.get("observed_at", "")),
        updated_at=str(node.metadata.get("updated_at", "")),
        confidence=_float_or_none(node.metadata.get("confidence")),
        provider_payload={"metadata": dict(node.metadata)},
    )


def _node_tags(node: GraphNode) -> tuple[str, ...]:
    tags = ["source", node.kind]
    freshness = node.metadata.get("freshness")
    if freshness:
        tags.append(str(freshness))
    if node.source_ref.path:
        tags.append("citation")
    return tuple(tags)


def _timestamps(metadata: object) -> dict[str, str]:
    if not isinstance(metadata, dict):
        return {}
    keys = ("created_at", "updated_at", "observed_at", "refreshed_at")
    return {key: str(metadata[key]) for key in keys if metadata.get(key)}


def _source_span(source_ref: SourceRef) -> str:
    if source_ref.line is None:
        return source_ref.section
    if source_ref.end_line and source_ref.end_line != source_ref.line:
        return f"{source_ref.line}-{source_ref.end_line}"
    return str(source_ref.line)


def _float_or_none(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "PragmaGraphLiveViewerProvider",
    "PragmaGraphViewerProvider",
]
