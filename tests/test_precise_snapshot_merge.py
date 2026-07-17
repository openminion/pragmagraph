from __future__ import annotations

from dataclasses import replace

import pytest

from pragmagraph.interchange import (
    ObservedSymbolFact,
    load_native_scip,
    merge_precise_snapshot,
    snapshot_from_compiler_facts,
)
from pragmagraph.models import PragmaGraphError
from pragmagraph.storage import stable_dumps
from .scip_fixtures import TYPESCRIPT_SCIP


def _base_snapshot(namespace: str = "fixture"):
    return snapshot_from_compiler_facts(
        (
            ObservedSymbolFact(
                symbol="local README#overview.",
                label="overview",
                path="README.md",
                kind="document_symbol",
            ),
        ),
        namespace=namespace,
        producer="local-indexer",
    )


def test_precise_merge_preserves_local_facts_and_is_byte_deterministic() -> None:
    base = _base_snapshot()
    precise = load_native_scip(TYPESCRIPT_SCIP, namespace="fixture").snapshot

    first = merge_precise_snapshot(base, precise)
    second = merge_precise_snapshot(base, precise)

    assert any(node.label == "overview" for node in first.nodes)
    assert any(node.metadata.get("scip_symbol") for node in first.nodes)
    assert all(
        edge.source_id in first.node_map() and edge.target_id in first.node_map()
        for edge in first.edges
    )
    assert stable_dumps(first) == stable_dumps(second)
    assert first.stats["precise_ingestion"]["producer"]["name"] == ("scip-typescript")


def test_precise_merge_preserves_base_on_ambiguous_exact_id_collision() -> None:
    precise = load_native_scip(TYPESCRIPT_SCIP, namespace="fixture").snapshot
    collided = next(node for node in precise.nodes if node.kind == "symbol")
    base = _base_snapshot()
    base = replace(base, nodes=(*base.nodes, replace(collided, label="base")))

    merged = merge_precise_snapshot(base, precise)

    assert merged.node_map()[collided.id].label == "base"
    collision = next(
        item for item in merged.omitted if item.reason == "precise_merge_collision"
    )
    assert collided.id in collision.details["node_ids"]


def test_precise_merge_rejects_namespace_mismatch() -> None:
    precise = load_native_scip(TYPESCRIPT_SCIP, namespace="precise").snapshot

    with pytest.raises(PragmaGraphError) as exc_info:
        merge_precise_snapshot(_base_snapshot(), precise)

    assert exc_info.value.code == "SCIP_NAMESPACE_MISMATCH"
