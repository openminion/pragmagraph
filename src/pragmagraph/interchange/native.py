"""Optional native SCIP protobuf intake for externally produced facts."""

from __future__ import annotations

import importlib
import importlib.util
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from pragmagraph._immutables import frozen_mapping, tuple_str
from pragmagraph.contracts import EDGE_MENTIONS, NODE_SYMBOL
from pragmagraph.interchange.compiler import (
    ObservedReferenceFact,
    ObservedSymbolFact,
    snapshot_from_compiler_facts,
)
from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, OmittedDiagnostic

SCIP_NATIVE_FORMAT = "scip.protobuf.v1"
SCIP_SCHEMA_REVISION = "e01e97efac2f6b8c266b4d04825f1f1eab7b8f6c"
SCIP_DEFINITION_ROLE = 1

FRESHNESS_MATCH = "match"
FRESHNESS_MISMATCH = "mismatch"
FRESHNESS_UNKNOWN = "unknown"
FRESHNESS_STATES = frozenset({FRESHNESS_MATCH, FRESHNESS_MISMATCH, FRESHNESS_UNKNOWN})

ACCEPTED_SCIP_FIELDS = (
    "metadata.version",
    "metadata.tool_info.name",
    "metadata.tool_info.version",
    "metadata.project_root",
    "metadata.text_document_encoding",
    "documents.language",
    "documents.relative_path",
    "documents.position_encoding",
    "documents.symbols.symbol",
    "documents.symbols.kind",
    "documents.symbols.display_name",
    "documents.symbols.enclosing_symbol",
    "documents.symbols.relationships",
    "documents.occurrences.range",
    "documents.occurrences.symbol",
    "documents.occurrences.symbol_roles",
    "documents.occurrences.syntax_kind",
    "external_symbols",
)


@dataclass(frozen=True)
class ScipProducer:
    """Observed producer identity from SCIP metadata."""

    name: str = ""
    version: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class ScipFreshness:
    """Exact root and commit comparison without semantic interpretation."""

    state: str = FRESHNESS_UNKNOWN
    root_state: str = FRESHNESS_UNKNOWN
    commit_state: str = FRESHNESS_UNKNOWN
    index_root: str = ""
    workspace_root: str = ""
    index_commit: str = ""
    workspace_commit: str = ""

    def __post_init__(self) -> None:
        for value in (self.state, self.root_state, self.commit_state):
            if value not in FRESHNESS_STATES:
                raise ValueError(f"unsupported SCIP freshness state: {value}")

    def to_dict(self) -> dict[str, str]:
        return {
            "state": self.state,
            "root_state": self.root_state,
            "commit_state": self.commit_state,
            "index_root": self.index_root,
            "workspace_root": self.workspace_root,
            "index_commit": self.index_commit,
            "workspace_commit": self.workspace_commit,
        }


@dataclass(frozen=True)
class ScipLossReport:
    """Accepted and omitted native SCIP field accounting."""

    accepted_fields: tuple[str, ...] = ACCEPTED_SCIP_FIELDS
    omitted_counts: Mapping[str, int] = field(default_factory=dict)
    malformed_counts: Mapping[str, int] = field(default_factory=dict)
    unknown_wire_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_fields", tuple_str(self.accepted_fields))
        object.__setattr__(self, "omitted_counts", frozen_mapping(self.omitted_counts))
        object.__setattr__(
            self, "malformed_counts", frozen_mapping(self.malformed_counts)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_fields": list(self.accepted_fields),
            "omitted_counts": dict(self.omitted_counts),
            "malformed_counts": dict(self.malformed_counts),
            "unknown_wire_bytes": self.unknown_wire_bytes,
        }


@dataclass(frozen=True)
class ScipIngestionReport:
    """Deterministic native SCIP intake evidence attached to a snapshot."""

    format: str = SCIP_NATIVE_FORMAT
    schema_revision: str = SCIP_SCHEMA_REVISION
    protocol_version: str = ""
    producer: ScipProducer = field(default_factory=ScipProducer)
    project_root: str = ""
    languages: tuple[str, ...] = ()
    document_count: int = 0
    symbol_count: int = 0
    reference_count: int = 0
    relationship_count: int = 0
    freshness: ScipFreshness = field(default_factory=ScipFreshness)
    loss: ScipLossReport = field(default_factory=ScipLossReport)

    def __post_init__(self) -> None:
        object.__setattr__(self, "languages", tuple(sorted(tuple_str(self.languages))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "schema_revision": self.schema_revision,
            "protocol_version": self.protocol_version,
            "producer": self.producer.to_dict(),
            "project_root": self.project_root,
            "languages": list(self.languages),
            "document_count": self.document_count,
            "symbol_count": self.symbol_count,
            "reference_count": self.reference_count,
            "relationship_count": self.relationship_count,
            "freshness": self.freshness.to_dict(),
            "loss": self.loss.to_dict(),
        }


@dataclass(frozen=True)
class NativeScipImport:
    """Canonical snapshot plus the native intake report that produced it."""

    snapshot: GraphSnapshot
    report: ScipIngestionReport


def native_scip_available() -> bool:
    """Return whether the optional protobuf runtime can load the pinned schema."""
    try:
        return (
            importlib.util.find_spec("google.protobuf") is not None
            and importlib.util.find_spec("pragmagraph.interchange._schema.scip_pb2")
            is not None
        )
    except ModuleNotFoundError:
        return False


def load_native_scip(
    path: str | Path,
    *,
    namespace: str = "scip",
    root_path: str = "",
    index_commit: str = "",
    workspace_commit: str = "",
    strict_freshness: bool = False,
) -> NativeScipImport:
    """Load one native ``index.scip`` file without launching an indexer."""
    source = Path(path)
    if not source.is_file():
        raise _error(
            "native SCIP file not found",
            "SCIP_INPUT_NOT_FOUND",
            {"path": str(source)},
        )
    return snapshot_from_scip_protobuf(
        source.read_bytes(),
        namespace=namespace,
        root_path=root_path,
        index_commit=index_commit,
        workspace_commit=workspace_commit,
        strict_freshness=strict_freshness,
    )


def snapshot_from_scip_protobuf(
    payload: bytes,
    *,
    namespace: str = "scip",
    root_path: str = "",
    index_commit: str = "",
    workspace_commit: str = "",
    strict_freshness: bool = False,
) -> NativeScipImport:
    """Decode a bounded native SCIP subset into canonical observed facts."""
    schema = _load_schema()
    index = _parse_index(payload, schema=schema)

    freshness = evaluate_scip_freshness(
        index_root=str(index.metadata.project_root or ""),
        workspace_root=root_path,
        index_commit=index_commit,
        workspace_commit=workspace_commit,
    )
    if strict_freshness and freshness.state == FRESHNESS_MISMATCH:
        raise _error(
            "native SCIP index does not match the requested workspace",
            "SCIP_FRESHNESS_MISMATCH",
            freshness.to_dict(),
        )

    unknown_wire_bytes = _unknown_wire_bytes(index)
    symbols, references, counts, diagnostics = _facts_from_index(index, schema)
    snapshot = snapshot_from_compiler_facts(
        tuple(symbols.values()),
        tuple(references),
        namespace=namespace,
        producer=str(index.metadata.tool_info.name or "scip"),
    )
    loss = ScipLossReport(
        omitted_counts=dict(sorted(counts["omitted"].items())),
        malformed_counts=dict(sorted(counts["malformed"].items())),
        unknown_wire_bytes=unknown_wire_bytes,
    )
    report = ScipIngestionReport(
        protocol_version=_enum_name(
            schema.ProtocolVersion,
            index.metadata.version,
        ),
        producer=ScipProducer(
            name=str(index.metadata.tool_info.name or ""),
            version=str(index.metadata.tool_info.version or ""),
        ),
        project_root=str(index.metadata.project_root or ""),
        languages=tuple(counts["languages"]),
        document_count=len(index.documents),
        symbol_count=len(symbols),
        reference_count=len(references),
        relationship_count=int(counts["relationship_count"]),
        freshness=freshness,
        loss=loss,
    )
    ingestion_diagnostics = tuple(
        OmittedDiagnostic(reason=reason, item_id=SCIP_NATIVE_FORMAT, details=details)
        for reason, details in diagnostics
    )
    snapshot = replace(
        snapshot,
        root_path=root_path,
        omitted=(*snapshot.omitted, *ingestion_diagnostics),
        stats={
            **dict(snapshot.stats),
            "precise_ingestion": report.to_dict(),
        },
    )
    return NativeScipImport(snapshot=snapshot, report=report)


def merge_precise_snapshot(
    base: GraphSnapshot,
    precise: GraphSnapshot,
) -> GraphSnapshot:
    """Compose exact precise facts into a base snapshot without fuzzy matching."""
    if base.namespace != precise.namespace:
        raise _error(
            "base and precise snapshots must use the same namespace",
            "SCIP_NAMESPACE_MISMATCH",
            {"base": base.namespace, "precise": precise.namespace},
        )
    nodes, node_collisions = _merge_records(base.nodes, precise.nodes)
    edges, edge_collisions = _merge_records(base.edges, precise.edges)
    node_ids = {item.id for item in nodes}
    missing_targets = tuple(
        sorted(
            item.id
            for item in edges
            if item.source_id not in node_ids or item.target_id not in node_ids
        )
    )
    diagnostics = list(base.omitted) + list(precise.omitted)
    if node_collisions or edge_collisions:
        diagnostics.append(
            OmittedDiagnostic(
                reason="precise_merge_collision",
                item_id=SCIP_NATIVE_FORMAT,
                details={
                    "node_ids": node_collisions,
                    "edge_ids": edge_collisions,
                    "resolution": "base_preserved",
                },
            )
        )
    if missing_targets:
        diagnostics.append(
            OmittedDiagnostic(
                reason="precise_merge_referential_gap",
                item_id=SCIP_NATIVE_FORMAT,
                details={"edge_ids": missing_targets},
            )
        )
        edges = tuple(item for item in edges if item.id not in set(missing_targets))
    return replace(
        base,
        nodes=nodes,
        edges=edges,
        omitted=tuple(
            sorted(diagnostics, key=lambda item: (item.reason, item.item_id))
        ),
        stats={
            **dict(base.stats),
            "precise_ingestion": dict(precise.stats.get("precise_ingestion", {})),
            "precise_merge": {
                "node_collision_count": len(node_collisions),
                "edge_collision_count": len(edge_collisions),
                "referential_gap_count": len(missing_targets),
            },
        },
    )


def evaluate_scip_freshness(
    *,
    index_root: str = "",
    workspace_root: str = "",
    index_commit: str = "",
    workspace_commit: str = "",
) -> ScipFreshness:
    """Compare exact root and commit identities with explicit unknown states."""
    root_state = _comparison_state(
        _normalized_root(index_root),
        _normalized_root(workspace_root),
    )
    commit_state = _comparison_state(index_commit.strip(), workspace_commit.strip())
    states = {root_state, commit_state}
    if FRESHNESS_MISMATCH in states:
        state = FRESHNESS_MISMATCH
    elif FRESHNESS_MATCH in states:
        state = FRESHNESS_MATCH
    else:
        state = FRESHNESS_UNKNOWN
    return ScipFreshness(
        state=state,
        root_state=root_state,
        commit_state=commit_state,
        index_root=index_root,
        workspace_root=workspace_root,
        index_commit=index_commit,
        workspace_commit=workspace_commit,
    )


def _facts_from_index(
    index: Any,
    schema: ModuleType,
) -> tuple[
    dict[str, ObservedSymbolFact],
    list[ObservedReferenceFact],
    dict[str, Any],
    list[tuple[str, dict[str, Any]]],
]:
    omitted: Counter[str] = Counter()
    malformed: Counter[str] = Counter()
    languages: set[str] = set()
    symbol_info = _collect_symbol_information(
        index,
        omitted=omitted,
        malformed=malformed,
        languages=languages,
    )
    symbols = _build_symbol_facts(symbol_info, schema=schema, omitted=omitted)
    references: list[ObservedReferenceFact] = []
    _collect_occurrence_facts(
        index,
        schema=schema,
        symbols=symbols,
        references=references,
        omitted=omitted,
        malformed=malformed,
    )
    relationship_count = _collect_relationship_facts(
        symbol_info,
        symbols=symbols,
        references=references,
        malformed=malformed,
    )
    return (
        symbols,
        references,
        {
            "omitted": omitted,
            "malformed": malformed,
            "languages": languages,
            "relationship_count": relationship_count,
        },
        _fact_diagnostics(omitted=omitted, malformed=malformed),
    )


def _collect_symbol_information(
    index: Any,
    *,
    omitted: Counter[str],
    malformed: Counter[str],
    languages: set[str],
) -> dict[str, tuple[Any, str]]:
    symbol_info: dict[str, tuple[Any, str]] = {}
    for information in index.external_symbols:
        symbol = str(information.symbol or "")
        if not symbol:
            malformed["external_symbol_missing_identity"] += 1
            continue
        symbol_info[symbol] = (information, "")
    for document in sorted(index.documents, key=lambda item: item.relative_path):
        path = str(document.relative_path or "")
        if not path:
            malformed["document_missing_relative_path"] += 1
        if document.language:
            languages.add(str(document.language))
        if document.text:
            omitted["document_text"] += 1
        for information in document.symbols:
            symbol = str(information.symbol or "")
            if not symbol:
                malformed["symbol_missing_identity"] += 1
                continue
            symbol_info[symbol] = (information, path)
    return symbol_info


def _build_symbol_facts(
    symbol_info: Mapping[str, tuple[Any, str]],
    *,
    schema: ModuleType,
    omitted: Counter[str],
) -> dict[str, ObservedSymbolFact]:
    symbols: dict[str, ObservedSymbolFact] = {}
    for symbol, (information, path) in sorted(symbol_info.items()):
        if information.documentation:
            omitted["symbol_documentation"] += len(information.documentation)
        if information.HasField("signature_documentation"):
            omitted["signature_documentation"] += 1
        metadata = {
            "scip_symbol": symbol,
            "scip_kind": _enum_name(schema.SymbolInformation.Kind, information.kind),
            "scip_external": not bool(path),
        }
        metadata.update(_symbol_package_metadata(symbol))
        if information.enclosing_symbol:
            metadata["scip_enclosing_symbol"] = information.enclosing_symbol
        symbols[symbol] = ObservedSymbolFact(
            symbol=symbol,
            label=str(information.display_name or symbol),
            path=path,
            kind=NODE_SYMBOL,
            metadata=metadata,
        )
    return symbols


def _collect_occurrence_facts(
    index: Any,
    *,
    schema: ModuleType,
    symbols: dict[str, ObservedSymbolFact],
    references: list[ObservedReferenceFact],
    omitted: Counter[str],
    malformed: Counter[str],
) -> None:
    definitions: set[str] = set()
    for document in sorted(index.documents, key=lambda item: item.relative_path):
        path = str(document.relative_path or "")
        ordered_occurrences = sorted(
            document.occurrences,
            key=lambda item: (_range_sort_key(item), str(item.symbol)),
        )
        for occurrence in ordered_occurrences:
            _record_occurrence(
                occurrence,
                path=path,
                schema=schema,
                symbols=symbols,
                references=references,
                definitions=definitions,
                omitted=omitted,
                malformed=malformed,
            )


def _record_occurrence(
    occurrence: Any,
    *,
    path: str,
    schema: ModuleType,
    symbols: dict[str, ObservedSymbolFact],
    references: list[ObservedReferenceFact],
    definitions: set[str],
    omitted: Counter[str],
    malformed: Counter[str],
) -> None:
    symbol = str(occurrence.symbol or "")
    if not symbol:
        malformed["occurrence_missing_symbol"] += 1
        return
    source_range = _native_occurrence_range(occurrence)
    if source_range is None:
        malformed["occurrence_invalid_range"] += 1
    line, column, end_line, end_column = source_range or (None,) * 4
    if occurrence.override_documentation:
        omitted["occurrence_override_documentation"] += len(
            occurrence.override_documentation
        )
    if occurrence.diagnostics:
        omitted["occurrence_diagnostics"] += len(occurrence.diagnostics)
    if symbol not in symbols:
        symbols[symbol] = _undeclared_symbol_fact(symbol)
        malformed["occurrence_symbol_information_missing"] += 1
    if int(occurrence.symbol_roles) & SCIP_DEFINITION_ROLE:
        if symbol in definitions:
            malformed["duplicate_symbol_definition"] += 1
            return
        definitions.add(symbol)
        symbols[symbol] = replace(
            symbols[symbol],
            path=path or symbols[symbol].path,
            line=line,
            column=column,
            end_line=end_line,
            end_column=end_column,
        )
        return
    references.append(
        ObservedReferenceFact(
            source_symbol="",
            target_symbol=symbol,
            path=path,
            kind=EDGE_MENTIONS,
            line=line,
            column=column,
            occurrence_id=_occurrence_identity(
                path,
                symbol,
                line,
                column,
                end_line,
                end_column,
            ),
            metadata={
                "scip_symbol_roles": int(occurrence.symbol_roles),
                "scip_syntax_kind": _enum_name(
                    schema.SyntaxKind,
                    occurrence.syntax_kind,
                ),
                "scip_range_encoding": _range_encoding(occurrence),
            },
        )
    )


def _collect_relationship_facts(
    symbol_info: Mapping[str, tuple[Any, str]],
    *,
    symbols: dict[str, ObservedSymbolFact],
    references: list[ObservedReferenceFact],
    malformed: Counter[str],
) -> int:
    relationship_count = 0
    for symbol, (information, _path) in sorted(symbol_info.items()):
        for relation_index, relationship in enumerate(information.relationships):
            target = str(relationship.symbol or "")
            if not target:
                malformed["relationship_missing_target"] += 1
                continue
            if target not in symbols:
                symbols[target] = _undeclared_symbol_fact(target)
            flags = _relationship_flags(relationship)
            references.append(
                ObservedReferenceFact(
                    source_symbol=symbol,
                    target_symbol=target,
                    path="",
                    kind=EDGE_MENTIONS,
                    occurrence_id=f"relationship:{relation_index}:{','.join(flags)}",
                    metadata={"scip_relationship": flags},
                )
            )
            relationship_count += 1
    return relationship_count


def _undeclared_symbol_fact(symbol: str) -> ObservedSymbolFact:
    return ObservedSymbolFact(
        symbol=symbol,
        label=symbol,
        path="",
        metadata={
            "scip_symbol": symbol,
            "scip_external": True,
            "scip_declaration_missing": True,
            **_symbol_package_metadata(symbol),
        },
    )


def _fact_diagnostics(
    *,
    omitted: Counter[str],
    malformed: Counter[str],
) -> list[tuple[str, dict[str, Any]]]:
    diagnostics: list[tuple[str, dict[str, Any]]] = []
    if omitted:
        diagnostics.append(
            ("unsupported_scip_fields", {"counts": dict(sorted(omitted.items()))})
        )
    if malformed:
        diagnostics.append(
            ("malformed_scip_facts", {"counts": dict(sorted(malformed.items()))})
        )
    return diagnostics


def _load_schema() -> ModuleType:
    try:
        return importlib.import_module("pragmagraph.interchange._schema.scip_pb2")
    except (ImportError, ModuleNotFoundError) as exc:
        raise _error(
            "native SCIP support requires the optional protobuf dependency",
            "SCIP_SUPPORT_UNAVAILABLE",
            {"install": "pragmagraph[scip]"},
        ) from exc


def _parse_index(payload: bytes, *, schema: ModuleType) -> Any:
    index = schema.Index()
    message_module = importlib.import_module("google.protobuf.message")
    decode_error = message_module.DecodeError
    try:
        index.ParseFromString(payload)
    except decode_error as exc:
        raise _error(
            "native SCIP protobuf is malformed",
            "SCIP_PAYLOAD_INVALID",
            {"error_type": type(exc).__name__},
        ) from exc
    return index


def _unknown_wire_bytes(index: Any) -> int:
    original_size = len(index.SerializeToString(deterministic=True))
    known = type(index)()
    known.CopyFrom(index)
    known.DiscardUnknownFields()
    known_size = len(known.SerializeToString(deterministic=True))
    return max(0, original_size - known_size)


def _native_occurrence_range(
    occurrence: Any,
) -> tuple[int, int, int, int] | None:
    typed = occurrence.WhichOneof("typed_range")
    if typed == "single_line_range":
        value = occurrence.single_line_range
        return (
            int(value.line) + 1,
            int(value.start_character) + 1,
            int(value.line) + 1,
            int(value.end_character) + 1,
        )
    if typed == "multi_line_range":
        value = occurrence.multi_line_range
        return (
            int(value.start_line) + 1,
            int(value.start_character) + 1,
            int(value.end_line) + 1,
            int(value.end_character) + 1,
        )
    values = tuple(int(item) for item in occurrence.range)
    if len(values) == 3:
        return (values[0] + 1, values[1] + 1, values[0] + 1, values[2] + 1)
    if len(values) == 4:
        return tuple(item + 1 for item in values)  # type: ignore[return-value]
    return None


def _range_sort_key(occurrence: Any) -> tuple[int, int, int, int]:
    return _native_occurrence_range(occurrence) or (0, 0, 0, 0)


def _range_encoding(occurrence: Any) -> str:
    return occurrence.WhichOneof("typed_range") or "deprecated_range"


def _occurrence_identity(
    path: str,
    symbol: str,
    line: int | None,
    column: int | None,
    end_line: int | None,
    end_column: int | None,
) -> str:
    return f"{path}:{line}:{column}:{end_line}:{end_column}:{symbol}"


def _symbol_package_metadata(symbol: str) -> dict[str, str]:
    parts = symbol.split(" ", 4)
    if len(parts) < 5 or symbol.startswith("local "):
        return {}
    return {
        "scip_scheme": parts[0],
        "scip_package_manager": parts[1],
        "scip_package_name": parts[2],
        "scip_package_version": parts[3],
    }


def _relationship_flags(relationship: Any) -> tuple[str, ...]:
    pairs = (
        ("reference", relationship.is_reference),
        ("implementation", relationship.is_implementation),
        ("type_definition", relationship.is_type_definition),
        ("definition", relationship.is_definition),
    )
    return tuple(name for name, enabled in pairs if enabled)


def _enum_name(enum: Any, value: int) -> str:
    try:
        return str(enum.Name(value))
    except ValueError:
        return f"UNKNOWN_{value}"


def _normalized_root(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme == "file":
        text = unquote(parsed.path)
    elif parsed.scheme:
        return text.rstrip("/")
    return str(Path(text).expanduser().resolve())


def _comparison_state(left: str, right: str) -> str:
    if not left or not right:
        return FRESHNESS_UNKNOWN
    return FRESHNESS_MATCH if left == right else FRESHNESS_MISMATCH


def _merge_records(
    base: tuple[GraphNode, ...] | tuple[GraphEdge, ...],
    precise: tuple[GraphNode, ...] | tuple[GraphEdge, ...],
) -> tuple[tuple[Any, ...], tuple[str, ...]]:
    records = {item.id: item for item in base}
    collisions: list[str] = []
    for item in precise:
        existing = records.get(item.id)
        if existing is None:
            records[item.id] = item
        elif existing.to_dict() != item.to_dict():
            collisions.append(item.id)
    return tuple(sorted(records.values(), key=lambda item: item.id)), tuple(
        sorted(collisions)
    )


def _error(
    message: str,
    code: str,
    details: Mapping[str, Any] | None = None,
) -> Exception:
    from pragmagraph.models import PragmaGraphError

    return PragmaGraphError(message, code=code, details=details or {})


__all__ = [
    "ACCEPTED_SCIP_FIELDS",
    "FRESHNESS_MATCH",
    "FRESHNESS_MISMATCH",
    "FRESHNESS_UNKNOWN",
    "NativeScipImport",
    "SCIP_NATIVE_FORMAT",
    "SCIP_SCHEMA_REVISION",
    "ScipFreshness",
    "ScipIngestionReport",
    "ScipLossReport",
    "ScipProducer",
    "evaluate_scip_freshness",
    "load_native_scip",
    "merge_precise_snapshot",
    "native_scip_available",
    "snapshot_from_scip_protobuf",
]
