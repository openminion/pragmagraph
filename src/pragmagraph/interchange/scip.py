"""Loss-aware JSON subset of the SCIP code-intelligence protocol."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any, Mapping

from pragmagraph.contracts import (
    EDGE_DEFINES,
    EDGE_MENTIONS,
    EDGE_RESOLVES_TO,
    NODE_SYMBOL,
    RESOLUTION_KIND_EXACT_SCIP_SYMBOL,
)
from pragmagraph.interchange.compiler import (
    ObservedReferenceFact,
    ObservedSymbolFact,
    snapshot_from_compiler_facts,
)
from pragmagraph.models import GraphSnapshot, OmittedDiagnostic, SourceRef

SCIP_JSON_SUBSET_FORMAT = "pragmagraph.scip_json_subset.v1alpha1"
SCIP_DEFINITION_ROLE = 1


def snapshot_to_scip_json(snapshot: GraphSnapshot) -> dict[str, Any]:
    """Export definitions and references as a deterministic SCIP-shaped subset."""
    documents: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"symbols": [], "occurrences": []}
    )
    symbol_ids = {
        node.id: str(node.metadata.get("symbol") or node.id)
        for node in snapshot.nodes
        if _is_symbol(node.kind) and node.source_ref.path
    }
    for node in sorted(snapshot.nodes, key=lambda item: item.id):
        symbol = symbol_ids.get(node.id)
        if symbol is None:
            continue
        document = documents[node.source_ref.path]
        document["symbols"].append(
            {
                "symbol": symbol,
                "display_name": node.label,
                "kind": node.kind,
            }
        )
        document["occurrences"].append(
            {
                "range": _scip_range(node.source_ref),
                "symbol": symbol,
                "symbol_roles": SCIP_DEFINITION_ROLE,
            }
        )
    omitted_references = 0
    omitted_cross_repo_resolutions = 0
    for edge in sorted(snapshot.edges, key=lambda item: item.id):
        if edge.kind == EDGE_DEFINES:
            continue
        if (
            edge.kind == EDGE_RESOLVES_TO
            and edge.metadata.get("resolution_kind")
            == RESOLUTION_KIND_EXACT_SCIP_SYMBOL
        ):
            omitted_cross_repo_resolutions += 1
            continue
        target_symbol = symbol_ids.get(edge.target_id)
        if target_symbol is None or not edge.source_ref.path:
            continue
        source_symbol = symbol_ids.get(edge.source_id)
        if source_symbol is None:
            omitted_references += 1
            continue
        documents[edge.source_ref.path]["occurrences"].append(
            {
                "range": _scip_range(edge.source_ref),
                "symbol": target_symbol,
                "symbol_roles": 0,
                "enclosing_symbol": source_symbol,
                "relationship": edge.kind,
            }
        )
    return {
        "format": SCIP_JSON_SUBSET_FORMAT,
        "metadata": {
            "project_root": "",
            "text_document_encoding": "UTF-8",
            "tool_info": {"name": "pragmagraph", "version": "subset-v1"},
        },
        "documents": [
            {
                "relative_path": path,
                "symbols": sorted(value["symbols"], key=lambda item: item["symbol"]),
                "occurrences": sorted(
                    value["occurrences"],
                    key=lambda item: (
                        item["range"],
                        item["symbol"],
                        item["symbol_roles"],
                    ),
                ),
            }
            for path, value in sorted(documents.items())
        ],
        "diagnostics": {
            "accepted_subset": [
                "metadata",
                "documents.relative_path",
                "documents.symbols",
                "documents.occurrences",
            ],
            "omitted_reference_count": omitted_references,
            "omitted_cross_repo_resolution_count": omitted_cross_repo_resolutions,
        },
    }


def snapshot_from_scip_json(
    payload: Mapping[str, Any],
    *,
    namespace: str = "scip",
) -> GraphSnapshot:
    """Import the accepted SCIP JSON subset into canonical observed facts."""
    symbols: dict[str, ObservedSymbolFact] = {}
    references: list[ObservedReferenceFact] = []
    unsupported = set(payload) - {"format", "metadata", "documents", "diagnostics"}
    documents = payload.get("documents", ())
    if not isinstance(documents, (list, tuple)):
        documents = ()
    for document in documents:
        if not isinstance(document, Mapping):
            continue
        unsupported.update(
            f"documents.{key}"
            for key in set(document) - {"relative_path", "symbols", "occurrences"}
        )
        path = str(document.get("relative_path", "") or "")
        for raw_symbol in document.get("symbols", ()) or ():
            if not isinstance(raw_symbol, Mapping):
                continue
            unsupported.update(
                f"documents.symbols.{key}"
                for key in set(raw_symbol) - {"symbol", "display_name", "kind"}
            )
            symbol = str(raw_symbol.get("symbol", "") or "")
            if symbol:
                symbols[symbol] = ObservedSymbolFact(
                    symbol=symbol,
                    label=str(raw_symbol.get("display_name", "") or symbol),
                    path=path,
                    kind=str(raw_symbol.get("kind", "") or NODE_SYMBOL),
                    metadata={"scip_symbol": symbol},
                )
        for occurrence in document.get("occurrences", ()) or ():
            if not isinstance(occurrence, Mapping):
                continue
            unsupported.update(
                f"documents.occurrences.{key}"
                for key in set(occurrence)
                - {
                    "range",
                    "symbol",
                    "symbol_roles",
                    "enclosing_symbol",
                    "relationship",
                }
            )
            symbol = str(occurrence.get("symbol", "") or "")
            role = int(occurrence.get("symbol_roles", 0) or 0)
            line, column, end_line, end_column = _source_range(occurrence.get("range"))
            if role & SCIP_DEFINITION_ROLE and symbol in symbols:
                fact = symbols[symbol]
                symbols[symbol] = ObservedSymbolFact(
                    symbol=fact.symbol,
                    label=fact.label,
                    path=path or fact.path,
                    kind=fact.kind,
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    metadata=fact.metadata,
                )
                continue
            enclosing = str(occurrence.get("enclosing_symbol", "") or "")
            if symbol and enclosing:
                references.append(
                    ObservedReferenceFact(
                        source_symbol=enclosing,
                        target_symbol=symbol,
                        path=path,
                        kind=str(occurrence.get("relationship", "") or EDGE_MENTIONS),
                        line=line,
                        column=column,
                        metadata={"scip_symbol_roles": role},
                    )
                )
    snapshot = snapshot_from_compiler_facts(
        tuple(symbols.values()),
        tuple(references),
        namespace=namespace,
        producer="scip_json_subset",
    )
    if not unsupported:
        return snapshot
    diagnostic = OmittedDiagnostic(
        reason="unsupported_scip_fields",
        item_id="scip_json_subset",
        details={"fields": tuple(sorted(unsupported))},
    )
    return replace(
        snapshot,
        omitted=(*snapshot.omitted, diagnostic),
        stats={**dict(snapshot.stats), "unsupported_field_count": len(unsupported)},
    )


def _is_symbol(kind: str) -> bool:
    return kind == NODE_SYMBOL or kind.endswith(
        ("_class", "_export", "_function", "_method", "_symbol")
    )


def _scip_range(source: SourceRef) -> list[int]:
    start_line = max(0, int(source.line or 1) - 1)
    start_column = max(0, int(source.column or 1) - 1)
    end_line = max(start_line, int(source.end_line or source.line or 1) - 1)
    end_column = max(start_column, int(source.end_column or source.column or 1) - 1)
    return [start_line, start_column, end_line, end_column]


def _source_range(value: Any) -> tuple[int | None, int | None, int | None, int | None]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None, None, None, None
    return tuple(int(item) + 1 for item in value)  # type: ignore[return-value]


__all__ = [
    "SCIP_DEFINITION_ROLE",
    "SCIP_JSON_SUBSET_FORMAT",
    "snapshot_from_scip_json",
    "snapshot_to_scip_json",
]
