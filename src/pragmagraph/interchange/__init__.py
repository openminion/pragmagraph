"""Stable symbol/reference interchange views for observed snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping
from pragmagraph.contracts import (
    EDGE_CALLS,
    EDGE_DEFINES,
    EDGE_DEPENDS_ON,
    EDGE_IMPORTS,
    EDGE_INHERITS,
    EDGE_MENTIONS,
    EDGE_PARENT_SYMBOL,
    EDGE_REFERENCES_DOC,
    EDGE_REFERENCES_SECTION,
)
from pragmagraph.models import GraphNode, GraphSnapshot, SourceRef

INTERCHANGE_FORMAT = "pragmagraph.symbol_reference.v1alpha1"
SYMBOL_NODE_SUFFIXES = ("_class", "_export", "_function", "_method", "_symbol")
REFERENCE_EDGE_KINDS = frozenset(
    {
        EDGE_CALLS,
        EDGE_DEFINES,
        EDGE_DEPENDS_ON,
        EDGE_IMPORTS,
        EDGE_INHERITS,
        EDGE_MENTIONS,
        EDGE_PARENT_SYMBOL,
        EDGE_REFERENCES_DOC,
        EDGE_REFERENCES_SECTION,
    }
)


@dataclass(frozen=True)
class SymbolRecord:
    """One stable symbol-like observed node."""

    symbol_id: str
    kind: str
    label: str
    source_ref: SourceRef = field(default_factory=SourceRef)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", frozen_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "kind": self.kind,
            "label": self.label,
            "source_ref": self.source_ref.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ReferenceRecord:
    """One stable structural reference edge."""

    reference_id: str
    kind: str
    source_id: str
    target_id: str
    source_ref: SourceRef = field(default_factory=SourceRef)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", frozen_mapping(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "kind": self.kind,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_ref": self.source_ref.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class InterchangeBundle:
    """Deterministic symbol/reference interchange payload."""

    format: str
    namespace: str
    symbols: tuple[SymbolRecord, ...] = ()
    references: tuple[ReferenceRecord, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbols", tuple(self.symbols))
        object.__setattr__(self, "references", tuple(self.references))
        object.__setattr__(self, "diagnostics", frozen_mapping(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "namespace": self.namespace,
            "symbols": [item.to_dict() for item in self.symbols],
            "references": [item.to_dict() for item in self.references],
            "diagnostics": dict(self.diagnostics),
        }


def build_symbol_reference_bundle(snapshot: GraphSnapshot) -> InterchangeBundle:
    """Build a stable symbol/reference payload from observed graph facts."""
    symbols = tuple(
        SymbolRecord(
            symbol_id=node.id,
            kind=node.kind,
            label=node.label,
            source_ref=node.source_ref,
            metadata=_symbol_metadata(node),
        )
        for node in sorted(snapshot.nodes, key=lambda item: item.id)
        if _is_symbol_node(node)
    )
    references = tuple(
        ReferenceRecord(
            reference_id=edge.id,
            kind=edge.kind,
            source_id=edge.source_id,
            target_id=edge.target_id,
            source_ref=edge.source_ref,
            metadata=dict(edge.metadata),
        )
        for edge in sorted(snapshot.edges, key=lambda item: item.id)
        if edge.kind in REFERENCE_EDGE_KINDS
    )
    return InterchangeBundle(
        format=INTERCHANGE_FORMAT,
        namespace=snapshot.namespace,
        symbols=symbols,
        references=references,
        diagnostics={
            "symbol_count": len(symbols),
            "reference_count": len(references),
            "omitted_count": len(snapshot.omitted),
            "reference_edge_kinds": sorted(REFERENCE_EDGE_KINDS),
        },
    )


def _is_symbol_node(node: GraphNode) -> bool:
    return node.kind.endswith(SYMBOL_NODE_SUFFIXES)


def _symbol_metadata(node: GraphNode) -> dict[str, Any]:
    keys = ("parser", "parser_version", "language", "module", "resolved")
    return {
        key: node.metadata[key]
        for key in keys
        if key in node.metadata and node.metadata[key] not in ("", None)
    }


from pragmagraph.interchange.compiler import (  # noqa: E402
    ObservedReferenceFact,
    ObservedSymbolFact,
    snapshot_from_compiler_facts,
)
from pragmagraph.interchange.scip import (  # noqa: E402
    SCIP_DEFINITION_ROLE,
    SCIP_JSON_SUBSET_FORMAT,
    snapshot_from_scip_json,
    snapshot_to_scip_json,
)


__all__ = [
    "INTERCHANGE_FORMAT",
    "InterchangeBundle",
    "ObservedReferenceFact",
    "ObservedSymbolFact",
    "REFERENCE_EDGE_KINDS",
    "ReferenceRecord",
    "SYMBOL_NODE_SUFFIXES",
    "SymbolRecord",
    "SCIP_DEFINITION_ROLE",
    "SCIP_JSON_SUBSET_FORMAT",
    "build_symbol_reference_bundle",
    "snapshot_from_compiler_facts",
    "snapshot_from_scip_json",
    "snapshot_to_scip_json",
]
