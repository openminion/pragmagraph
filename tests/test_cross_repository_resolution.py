from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from pragmagraph.contracts import (
    EDGE_MENTIONS,
    EDGE_RESOLVES_TO,
    NODE_PROJECT,
    NODE_SYMBOL,
    RESOLUTION_KIND_EXACT_SCIP_SYMBOL,
)
from pragmagraph.interchange import (
    build_symbol_reference_bundle,
    parse_scip_symbol,
    require_cross_repository_symbol,
    snapshot_to_scip_json,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    PragmaGraphError,
    SourceRef,
)
from pragmagraph.portability import edge_id, node_id
from pragmagraph.query import (
    cross_repo_resolution_diagnostics,
    incoming_external_symbols,
    neighborhood,
    path,
    resolved_definition,
)
from pragmagraph.report import build_report
from pragmagraph.storage import stable_dumps
from pragmagraph.viewer import build_viewer_envelope
from pragmagraph.workspace import (
    NamedSnapshot,
    compose_snapshots,
    save_composed_snapshot_atomic,
)

FIXTURES = Path(__file__).parent / "fixtures" / "cross_repository"


def _fixture(name: str) -> dict[str, str]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _snapshot(
    namespace: str,
    facts: tuple[tuple[str, str, bool, str, int | None], ...],
) -> GraphSnapshot:
    project = GraphNode(
        id=node_id(namespace, NODE_PROJECT, "."),
        kind=NODE_PROJECT,
        label=namespace,
        source_ref=SourceRef(path="."),
    )
    symbols = tuple(
        GraphNode(
            id=node_id(namespace, NODE_SYMBOL, key),
            kind=NODE_SYMBOL,
            label=key,
            source_ref=SourceRef(path=path, line=line),
            metadata={"scip_symbol": symbol, "scip_external": external},
        )
        for key, symbol, external, path, line in facts
    )
    return GraphSnapshot(namespace=namespace, root_path="", nodes=(project, *symbols))


@pytest.mark.parametrize("fixture_name", ("python", "typescript"))
def test_certified_language_pairs_resolve_exact_symbols(fixture_name: str) -> None:
    fixture = _fixture(fixture_name)
    symbol = fixture["symbol"]
    consumer = _snapshot("consumer", (("external", symbol, True, "", None),))
    consumer = replace(
        consumer,
        nodes=tuple(
            replace(
                node,
                metadata={**dict(node.metadata), "scip_package_version": "tampered"},
            )
            if node.kind == NODE_SYMBOL
            else node
            for node in consumer.nodes
        ),
    )
    provider = _snapshot("provider", (("definition", symbol, False, "src/service", 7),))

    result = compose_snapshots(
        (NamedSnapshot("consumer", consumer), NamedSnapshot("provider", provider))
    )

    edge = next(edge for edge in result.snapshot.edges if edge.kind == EDGE_RESOLVES_TO)
    assert edge.metadata["resolution_kind"] == RESOLUTION_KIND_EXACT_SCIP_SYMBOL
    assert edge.metadata["scip_package_version"] == "1.0.0"
    assert result.report.outcome_counts["cross_repo_definition_exact"] == 1
    assert resolved_definition(result.snapshot, edge.source_id).id == edge.target_id
    assert (
        incoming_external_symbols(result.snapshot, edge.target_id)[0].id
        == edge.source_id
    )
    assert fixture["license"] == "Apache-2.0"


def test_scip_identity_parser_handles_escaping_placeholders_and_locals() -> None:
    escaped = "scip-test pkg  manager package  name 1.0.0 `a``b`/run()."
    identity = parse_scip_symbol(escaped)

    assert identity.to_symbol() == escaped
    assert identity.package_manager == "pkg manager"
    assert identity.package_name == "package name"
    assert identity.descriptors == ("`a``b`/", "run().")
    assert parse_scip_symbol("local temp_1").is_local is True
    assert parse_scip_symbol("scip-test . . . value#").has_complete_package is False
    with pytest.raises(PragmaGraphError) as placeholder:
        require_cross_repository_symbol("scip-test . . . value#")
    assert placeholder.value.code == "INVALID_SCIP_SYMBOL"
    with pytest.raises(PragmaGraphError):
        parse_scip_symbol("scip-test npm pkg 1.0.0 `simple`#")


def test_resolution_outcomes_are_exact_typed_and_never_guess() -> None:
    exact = "scip-python python pkg 1.0.0 pkg/service#serve()."
    other_version = "scip-python python pkg 2.0.0 pkg/service#serve()."
    missing = "scip-python python missing 1.0.0 pkg/missing#call()."
    consumers = _snapshot(
        "consumers",
        (
            ("exact", exact, True, "", None),
            ("version", exact, True, "", None),
            ("missing", missing, True, "", None),
            ("invalid", "not-a-scip-symbol", True, "", None),
            ("local", "local item", True, "", None),
        ),
    )
    mismatch_provider = _snapshot(
        "mismatch", (("v2", other_version, False, "service.py", 1),)
    )
    result = compose_snapshots(
        (
            NamedSnapshot("consumers", consumers),
            NamedSnapshot("mismatch", mismatch_provider),
        )
    )

    counts = result.report.outcome_counts
    assert counts["cross_repo_package_version_mismatch"] == 2
    assert counts["cross_repo_definition_missing"] == 1
    assert counts["cross_repo_identity_invalid"] == 2
    assert counts["cross_repo_definition_exact"] == 0
    assert not any(edge.kind == EDGE_RESOLVES_TO for edge in result.snapshot.edges)
    reasons = {
        item.reason for item in cross_repo_resolution_diagnostics(result.snapshot)
    }
    assert "cross_repo_package_version_mismatch" in reasons
    assert "cross_repo_identity_invalid" in reasons


def test_ambiguous_and_same_root_candidates_do_not_create_edges() -> None:
    symbol = "scip-typescript npm pkg 1.0.0 src/service#serve()."
    consumer = _snapshot("consumer", (("external", symbol, True, "", None),))
    first = _snapshot("first", (("first", symbol, False, "a.ts", 1),))
    second = _snapshot("second", (("second", symbol, False, "b.ts", 1),))
    ambiguous = compose_snapshots(
        (
            NamedSnapshot("consumer", consumer),
            NamedSnapshot("first", first),
            NamedSnapshot("second", second),
        )
    )
    same_root = _snapshot(
        "same",
        (
            ("external", symbol, True, "", None),
            ("definition", symbol, False, "same.ts", 1),
        ),
    )
    local = compose_snapshots((NamedSnapshot("same", same_root),))

    assert ambiguous.report.outcome_counts["cross_repo_definition_ambiguous"] == 1
    assert local.report.outcome_counts["cross_repo_definition_same_root"] == 1
    assert not any(edge.kind == EDGE_RESOLVES_TO for edge in ambiguous.snapshot.edges)
    assert not any(edge.kind == EDGE_RESOLVES_TO for edge in local.snapshot.edges)


def test_composition_is_input_order_and_timezone_stable() -> None:
    symbol = _fixture("python")["symbol"]
    consumer = NamedSnapshot(
        "consumer", _snapshot("consumer", (("external", symbol, True, "", None),))
    )
    provider = NamedSnapshot(
        "provider",
        _snapshot("provider", (("definition", symbol, False, "service.py", 1),)),
    )
    previous_tz = os.environ.get("TZ")
    try:
        os.environ["TZ"] = "Pacific/Honolulu"
        first = stable_dumps(compose_snapshots((consumer, provider)).snapshot)
        os.environ["TZ"] = "Asia/Tokyo"
        second = stable_dumps(compose_snapshots((provider, consumer)).snapshot)
    finally:
        if previous_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous_tz

    assert first == second
    payload = json.loads(first)
    assert payload["root_path"] == ""
    assert payload["created_at"] == ""
    assert [item["name"] for item in payload["stats"]["workspace_roots"]] == [
        "consumer",
        "provider",
    ]


def test_composition_rejects_invalid_envelopes_before_merging() -> None:
    symbol = _fixture("python")["symbol"]
    snapshot = _snapshot("one", (("definition", symbol, False, "one.py", 1),))
    nested = replace(
        snapshot,
        stats={"cross_repo_resolution_schema_version": "existing"},
    )
    missing_project = replace(
        snapshot,
        nodes=tuple(node for node in snapshot.nodes if node.kind != NODE_PROJECT),
    )

    with pytest.raises(PragmaGraphError) as duplicate:
        compose_snapshots(
            (NamedSnapshot("one", snapshot), NamedSnapshot("one", snapshot))
        )
    assert duplicate.value.code == "DUPLICATE_SNAPSHOT_INPUT"
    same_namespace = replace(snapshot, nodes=tuple(snapshot.nodes))
    with pytest.raises(PragmaGraphError) as namespace_error:
        compose_snapshots(
            (NamedSnapshot("one", snapshot), NamedSnapshot("two", same_namespace))
        )
    assert namespace_error.value.code == "DUPLICATE_SNAPSHOT_NAMESPACE"
    with pytest.raises(PragmaGraphError) as nested_error:
        compose_snapshots((NamedSnapshot("nested", nested),))
    assert nested_error.value.code == "NESTED_SNAPSHOT_COMPOSITION"
    with pytest.raises(PragmaGraphError) as project_error:
        compose_snapshots((NamedSnapshot("invalid", missing_project),))
    assert project_error.value.code == "INVALID_PROJECT_NODE_COUNT"

    wrong_schema = replace(snapshot, schema_version="future")
    with pytest.raises(PragmaGraphError) as schema_error:
        compose_snapshots((NamedSnapshot("future", wrong_schema),))
    assert schema_error.value.code == "UNSUPPORTED_SCHEMA_VERSION"

    dangling = replace(
        snapshot,
        edges=(
            GraphEdge(
                id=edge_id("one", "missing", EDGE_MENTIONS, "also-missing"),
                kind=EDGE_MENTIONS,
                source_id="missing",
                target_id="also-missing",
            ),
        ),
    )
    with pytest.raises(PragmaGraphError) as gap_error:
        compose_snapshots((NamedSnapshot("dangling", dangling),))
    assert gap_error.value.code == "SNAPSHOT_REFERENTIAL_GAP"

    other = _snapshot("two", (("definition", symbol, False, "two.py", 1),))
    first_symbol_id = next(
        node.id for node in snapshot.nodes if node.kind == NODE_SYMBOL
    )
    colliding_nodes = tuple(
        replace(node, id=first_symbol_id) if node.kind == NODE_SYMBOL else node
        for node in other.nodes
    )
    with pytest.raises(PragmaGraphError) as collision_error:
        compose_snapshots(
            (
                NamedSnapshot("one", snapshot),
                NamedSnapshot("two", replace(other, nodes=colliding_nodes)),
            )
        )
    assert collision_error.value.code == "DUPLICATE_NODE_ID"


def test_diagnostic_and_ambiguity_samples_are_bounded_with_exact_counts() -> None:
    missing_facts = tuple(
        (
            f"missing-{index:03d}",
            f"scip-python python missing-{index:03d} 1.0.0 pkg/item#call().",
            True,
            "",
            None,
        )
        for index in range(105)
    )
    ambiguous_symbol = "scip-python python shared 1.0.0 pkg/item#call()."
    consumer = NamedSnapshot(
        "consumer",
        _snapshot(
            "consumer",
            (*missing_facts, ("ambiguous", ambiguous_symbol, True, "", None)),
        ),
    )
    providers = tuple(
        NamedSnapshot(
            f"provider-{index:02d}",
            _snapshot(
                f"provider-{index:02d}",
                (("definition", ambiguous_symbol, False, "item.py", 1),),
            ),
        )
        for index in range(25)
    )

    result = compose_snapshots((consumer, *providers))
    missing = [
        item
        for item in result.snapshot.omitted
        if item.reason == "cross_repo_definition_missing"
    ]
    ambiguous = next(
        item
        for item in result.snapshot.omitted
        if item.reason == "cross_repo_definition_ambiguous"
    )

    assert result.report.outcome_counts["cross_repo_definition_missing"] == 105
    assert result.report.omitted_detail_counts["cross_repo_definition_missing"] == 5
    assert len(missing) == 100
    assert len(ambiguous.details["candidate_ids"]) == 20
    assert ambiguous.details["omitted_candidate_count"] == 5


def test_atomic_save_cleans_temporary_file_and_preserves_destination_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(
        "one", (("item", _fixture("python")["symbol"], False, "a.py", 1),)
    )
    target = tmp_path / "workspace.json"
    target.write_text("existing\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"cannot replace {source} with {destination}")

    monkeypatch.setattr("pragmagraph.workspace.composition.os.replace", fail_replace)
    with pytest.raises(OSError):
        save_composed_snapshot_atomic(snapshot, target)

    assert target.read_text(encoding="utf-8") == "existing\n"
    assert not tuple(tmp_path.glob(".workspace.json.*.tmp"))


def test_interchange_preserves_resolution_edge_and_scip_reports_omission() -> None:
    symbol = _fixture("typescript")["symbol"]
    result = compose_snapshots(
        (
            NamedSnapshot(
                "consumer",
                _snapshot("consumer", (("external", symbol, True, "", None),)),
            ),
            NamedSnapshot(
                "provider",
                _snapshot(
                    "provider", (("definition", symbol, False, "service.ts", 1),)
                ),
            ),
        )
    )

    bundle = build_symbol_reference_bundle(result.snapshot)
    scip = snapshot_to_scip_json(result.snapshot)

    assert any(item.kind == EDGE_RESOLVES_TO for item in bundle.references)
    assert scip["diagnostics"]["omitted_cross_repo_resolution_count"] == 1


def test_existing_navigation_report_and_viewer_consume_resolution_edges() -> None:
    symbol = _fixture("python")["symbol"]
    result = compose_snapshots(
        (
            NamedSnapshot(
                "consumer",
                _snapshot("consumer", (("external", symbol, True, "", None),)),
            ),
            NamedSnapshot(
                "provider",
                _snapshot(
                    "provider", (("definition", symbol, False, "service.py", 1),)
                ),
            ),
        )
    )
    resolution = next(
        edge for edge in result.snapshot.edges if edge.kind == EDGE_RESOLVES_TO
    )
    neighbors = neighborhood(
        result.snapshot, resolution.source_id, depth=1, max_results=20
    )
    resolved_path = path(
        result.snapshot, resolution.source_id, resolution.target_id, max_hops=1
    )
    report = build_report(result.snapshot)
    viewer = build_viewer_envelope(result.snapshot, level_of_detail="raw")

    assert resolution.target_id in {hit.node.id for hit in neighbors.hits}
    assert [edge.id for edge in resolved_path.edges] == [resolution.id]
    assert report.summary.edge_kinds[EDGE_RESOLVES_TO] == 1
    assert any(edge["kind"] == EDGE_RESOLVES_TO for edge in viewer.edges)
