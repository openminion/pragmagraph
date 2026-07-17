"""Caller-fed exact compiler and language-server fact bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph.contracts import (
    EDGE_CONTAINS,
    EDGE_DEFINES,
    EDGE_MENTIONS,
    NODE_FILE,
    NODE_PROJECT,
    NODE_SYMBOL,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OmittedDiagnostic,
    SourceRef,
)
from pragmagraph.portability import edge_id, node_id


@dataclass(frozen=True)
class ObservedSymbolFact:
    """One exact symbol fact produced by an external static-analysis tool."""

    symbol: str
    label: str
    path: str
    kind: str = NODE_SYMBOL
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservedReferenceFact:
    """One exact source-to-target reference from an external producer."""

    source_symbol: str
    target_symbol: str
    path: str
    kind: str = EDGE_MENTIONS
    line: int | None = None
    column: int | None = None
    occurrence_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


def snapshot_from_compiler_facts(
    symbols: tuple[ObservedSymbolFact, ...],
    references: tuple[ObservedReferenceFact, ...] = (),
    *,
    namespace: str = "compiler",
    producer: str = "external",
) -> GraphSnapshot:
    """Build a canonical snapshot from already-observed precise facts."""
    project_id = node_id(namespace, NODE_PROJECT, ".")
    nodes: dict[str, GraphNode] = {
        project_id: GraphNode(
            id=project_id,
            kind=NODE_PROJECT,
            label=namespace,
            source_ref=SourceRef(path="."),
            metadata={"producer": producer},
        )
    }
    edges: dict[str, GraphEdge] = {}
    file_ids: dict[str, str] = {}
    symbol_ids: dict[str, str] = {}
    omitted: list[OmittedDiagnostic] = []
    for fact in sorted(symbols, key=lambda item: (item.path, item.symbol)):
        file_id = (
            _ensure_file(namespace, fact.path, project_id, nodes, edges, file_ids)
            if fact.path
            else ""
        )
        symbol_id = _add_symbol_fact(
            fact,
            namespace=namespace,
            producer=producer,
            file_id=file_id,
            nodes=nodes,
            edges=edges,
        )
        symbol_ids[fact.symbol] = symbol_id
    for fact in sorted(
        references,
        key=lambda item: (item.path, item.source_symbol, item.target_symbol),
    ):
        source_id = _reference_source_id(
            fact,
            namespace=namespace,
            project_id=project_id,
            nodes=nodes,
            edges=edges,
            file_ids=file_ids,
            symbol_ids=symbol_ids,
        )
        target_id = symbol_ids.get(fact.target_symbol)
        if source_id is None or target_id is None:
            omitted.append(
                OmittedDiagnostic(
                    reason="compiler_reference_unresolved",
                    item_id=f"{fact.source_symbol}->{fact.target_symbol}",
                    details={"producer": producer, "path": fact.path},
                )
            )
            continue
        reference_identity = (
            f"{target_id}:{fact.occurrence_id}" if fact.occurrence_id else target_id
        )
        reference_id = edge_id(
            namespace,
            source_id,
            fact.kind,
            reference_identity,
        )
        edges[reference_id] = GraphEdge(
            id=reference_id,
            kind=fact.kind,
            source_id=source_id,
            target_id=target_id,
            source_ref=SourceRef(path=fact.path, line=fact.line, column=fact.column),
            metadata={**dict(fact.metadata), "producer": producer},
        )
    return GraphSnapshot(
        namespace=namespace,
        root_path="",
        nodes=tuple(sorted(nodes.values(), key=lambda item: item.id)),
        edges=tuple(sorted(edges.values(), key=lambda item: item.id)),
        omitted=tuple(omitted),
        stats={
            "producer": producer,
            "symbol_count": len(symbols),
            "reference_count": len(references),
            "unresolved_reference_count": len(omitted),
        },
    )


def _add_symbol_fact(
    fact: ObservedSymbolFact,
    *,
    namespace: str,
    producer: str,
    file_id: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
) -> str:
    symbol_id = node_id(namespace, fact.kind, fact.symbol)
    source_ref = SourceRef(
        path=fact.path,
        line=fact.line,
        column=fact.column,
        end_line=fact.end_line,
        end_column=fact.end_column,
    )
    nodes[symbol_id] = GraphNode(
        id=symbol_id,
        kind=fact.kind,
        label=fact.label,
        source_ref=source_ref,
        metadata={
            **dict(fact.metadata),
            "producer": producer,
            "symbol": fact.symbol,
        },
    )
    if file_id:
        defines_id = edge_id(namespace, file_id, EDGE_DEFINES, symbol_id)
        edges[defines_id] = GraphEdge(
            id=defines_id,
            kind=EDGE_DEFINES,
            source_id=file_id,
            target_id=symbol_id,
            source_ref=source_ref,
            metadata={"producer": producer},
        )
    return symbol_id


def _reference_source_id(
    fact: ObservedReferenceFact,
    *,
    namespace: str,
    project_id: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    file_ids: dict[str, str],
    symbol_ids: dict[str, str],
) -> str | None:
    source_id = symbol_ids.get(fact.source_symbol)
    if source_id is not None or fact.source_symbol or not fact.path:
        return source_id
    return _ensure_file(
        namespace,
        fact.path,
        project_id,
        nodes,
        edges,
        file_ids,
    )


def _ensure_file(
    namespace: str,
    path: str,
    project_id: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    file_ids: dict[str, str],
) -> str:
    if path in file_ids:
        return file_ids[path]
    file_id = node_id(namespace, NODE_FILE, path)
    file_ids[path] = file_id
    nodes[file_id] = GraphNode(
        id=file_id,
        kind=NODE_FILE,
        label=path.rsplit("/", 1)[-1],
        source_ref=SourceRef(path=path),
    )
    contains_id = edge_id(namespace, project_id, EDGE_CONTAINS, file_id)
    edges[contains_id] = GraphEdge(
        id=contains_id,
        kind=EDGE_CONTAINS,
        source_id=project_id,
        target_id=file_id,
        source_ref=SourceRef(path=path),
    )
    return file_id


__all__ = [
    "ObservedReferenceFact",
    "ObservedSymbolFact",
    "snapshot_from_compiler_facts",
]
