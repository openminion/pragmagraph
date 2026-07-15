from __future__ import annotations

from pragmagraph.interchange import (
    ObservedReferenceFact,
    ObservedSymbolFact,
    snapshot_from_compiler_facts,
    snapshot_from_scip_json,
    snapshot_to_scip_json,
)


def _compiler_snapshot():
    return snapshot_from_compiler_facts(
        (
            ObservedSymbolFact(
                symbol="pkg/Service#serve().",
                label="serve",
                path="service.py",
                kind="python_function",
                line=1,
                column=1,
                end_line=1,
                end_column=6,
            ),
            ObservedSymbolFact(
                symbol="pkg/Client#load().",
                label="load",
                path="client.py",
                kind="python_function",
                line=3,
                column=1,
                end_line=3,
                end_column=5,
            ),
        ),
        (
            ObservedReferenceFact(
                source_symbol="pkg/Client#load().",
                target_symbol="pkg/Service#serve().",
                path="client.py",
                kind="calls",
                line=4,
                column=5,
            ),
        ),
        namespace="precise",
        producer="fixture-compiler",
    )


def test_compiler_fact_bridge_preserves_exact_provenance() -> None:
    snapshot = _compiler_snapshot()

    assert snapshot.stats == {
        "producer": "fixture-compiler",
        "symbol_count": 2,
        "reference_count": 1,
        "unresolved_reference_count": 0,
    }
    call = next(edge for edge in snapshot.edges if edge.kind == "calls")
    assert call.source_ref.path == "client.py"
    assert call.source_ref.line == 4


def test_scip_json_subset_round_trip_preserves_symbols_and_references() -> None:
    payload = snapshot_to_scip_json(_compiler_snapshot())
    restored = snapshot_from_scip_json(payload, namespace="restored")

    symbols = [node for node in restored.nodes if node.kind == "python_function"]
    references = [edge for edge in restored.edges if edge.kind == "calls"]
    assert len(symbols) == 2
    assert len(references) == 1
    assert payload["metadata"]["project_root"] == ""
    assert payload["diagnostics"]["omitted_reference_count"] == 0


def test_scip_subset_reports_unsupported_fields() -> None:
    payload = snapshot_to_scip_json(_compiler_snapshot())
    payload["external_symbols"] = [{"symbol": "external"}]

    restored = snapshot_from_scip_json(payload)

    assert restored.omitted[-1].reason == "unsupported_scip_fields"
    assert restored.omitted[-1].details["fields"] == ("external_symbols",)
