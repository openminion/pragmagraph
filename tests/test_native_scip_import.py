from __future__ import annotations

import pytest

from pragmagraph.interchange import load_native_scip, snapshot_from_scip_protobuf
from pragmagraph.interchange._schema import scip_pb2
from pragmagraph.models import PragmaGraphError
from .scip_fixtures import TYPESCRIPT_SCIP


def test_native_scip_import_decodes_observed_symbols_ranges_and_references() -> None:
    result = load_native_scip(TYPESCRIPT_SCIP, namespace="fixture")
    symbols = {
        str(node.metadata.get("scip_symbol")): node
        for node in result.snapshot.nodes
        if node.kind == "symbol"
    }
    run_symbol = next(symbol for symbol in symbols if symbol.endswith("run()."))
    serve_symbol = next(symbol for symbol in symbols if symbol.endswith("serve()."))
    references = [edge for edge in result.snapshot.edges if edge.kind == "mentions"]

    assert result.report.producer.name == "scip-typescript"
    assert result.report.producer.version == "0.4.0"
    assert symbols[run_symbol].source_ref.to_dict() == {
        "path": "src/client.ts",
        "line": 3,
        "column": 17,
        "end_line": 3,
        "end_column": 20,
        "section": "",
        "uri": "",
    }
    assert symbols[serve_symbol].metadata["scip_package_name"] == (
        "pgpi-typescript-fixture"
    )
    assert any(
        edge.source_ref.path == "src/client.ts"
        and edge.target_id == symbols[serve_symbol].id
        for edge in references
    )
    assert result.report.loss.omitted_counts == {"symbol_documentation": 4}


def test_native_scip_import_groups_unsupported_malformed_and_unknown_fields() -> None:
    index = scip_pb2.Index()
    index.metadata.tool_info.name = "fixture"
    document = index.documents.add(relative_path="src/app.py", text="secret")
    document.symbols.add(symbol="fixture python pkg 1 app/run().", display_name="run")
    occurrence = document.occurrences.add(symbol="fixture python pkg 1 app/run().")
    occurrence.range.extend((0, 0, 3))
    occurrence.symbol_roles = 1
    occurrence.override_documentation.append("omitted")
    occurrence.diagnostics.add(message="omitted")
    document.occurrences.add()
    payload = index.SerializeToString(deterministic=True) + b"\x98\x06\x01"

    result = snapshot_from_scip_protobuf(payload)

    assert result.report.loss.omitted_counts == {
        "document_text": 1,
        "occurrence_diagnostics": 1,
        "occurrence_override_documentation": 1,
    }
    assert result.report.loss.malformed_counts == {"occurrence_missing_symbol": 1}
    assert result.report.loss.unknown_wire_bytes == 3
    assert {item.reason for item in result.snapshot.omitted} == {
        "malformed_scip_facts",
        "unsupported_scip_fields",
    }


def test_native_scip_import_rejects_malformed_payload() -> None:
    with pytest.raises(PragmaGraphError) as exc_info:
        snapshot_from_scip_protobuf(b"\x0a\xff")

    assert exc_info.value.code == "SCIP_PAYLOAD_INVALID"
