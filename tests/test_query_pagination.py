from __future__ import annotations

from dataclasses import replace

import pytest

from pragmagraph.models import GraphNode, GraphSnapshot, PragmaGraphError, QueryRequest
from pragmagraph.query import query
from pragmagraph.server.backend import ServiceConfig, build_wired_registry
from pragmagraph.storage import SQLiteGraphStore, save_snapshot


def _snapshot() -> GraphSnapshot:
    return GraphSnapshot(
        namespace="cursor-test",
        root_path=".",
        nodes=tuple(
            GraphNode(id=f"node:{index}", kind="file", label=f"Graph {index}")
            for index in range(5)
        ),
    )


def test_query_cursor_pages_concatenate_to_canonical_order() -> None:
    snapshot = _snapshot()
    expected = query(snapshot, QueryRequest(query="Graph", max_results=10))
    request = QueryRequest(query="Graph", max_results=2)

    first = query(snapshot, request)
    second = query(snapshot, replace(request, cursor=first.next_cursor))
    third = query(snapshot, replace(request, cursor=second.next_cursor))

    assert [hit.node.id for page in (first, second, third) for hit in page.hits] == [
        hit.node.id for hit in expected.hits
    ]
    assert first.next_cursor
    assert second.next_cursor
    assert third.next_cursor == ""
    assert third.diagnostics["page_complete"] is True


def test_query_cursor_rejects_request_mismatch_and_malformed_data() -> None:
    snapshot = _snapshot()
    first = query(snapshot, QueryRequest(query="Graph", max_results=2))

    with pytest.raises(PragmaGraphError, match="does not match") as mismatch:
        query(
            snapshot,
            QueryRequest(query="Other", max_results=2, cursor=first.next_cursor),
        )
    assert mismatch.value.code == "QUERY_CURSOR_MISMATCH"

    with pytest.raises(PragmaGraphError, match="malformed") as malformed:
        query(snapshot, QueryRequest(query="Graph", cursor="not-base64"))
    assert malformed.value.code == "INVALID_QUERY_CURSOR"

    with pytest.raises(PragmaGraphError, match="does not match") as budget_mismatch:
        query(
            snapshot,
            QueryRequest(
                query="Graph",
                max_results=2,
                max_examined=5,
                cursor=first.next_cursor,
            ),
        )
    assert budget_mismatch.value.code == "QUERY_CURSOR_MISMATCH"


def test_query_work_budget_refuses_partial_ranking() -> None:
    result = query(
        _snapshot(),
        QueryRequest(query="Graph", max_results=2, max_examined=3),
    )

    assert result.hits == ()
    assert result.omitted[0].reason == "work_budget_exhausted"
    assert result.diagnostics == {
        "candidate_count": 5,
        "examined_count": 0,
        "page_complete": False,
        "work_budget_exhausted": True,
    }


def test_sqlite_query_preserves_page_cursor(tmp_path) -> None:
    store = SQLiteGraphStore.from_snapshot(_snapshot(), tmp_path / "graph.sqlite3")
    request = QueryRequest(query="Graph", max_results=2)

    first = store.query(request)
    second = store.query(replace(request, cursor=first.next_cursor))

    assert first.next_cursor
    assert [hit.node.id for hit in first.hits] != [hit.node.id for hit in second.hits]
    assert second.diagnostics["snapshot_deserialized"] is False


def test_mcp_query_accepts_cursor_and_work_budget(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(_snapshot(), snapshot_path)
    registry = build_wired_registry(ServiceConfig(snapshot_path=str(snapshot_path)))
    handler = registry.get_handler("pragmagraph_query")

    first = handler(text="Graph", max_results=2, max_examined=5)["query_result"]
    second = handler(
        text="Graph",
        max_results=2,
        max_examined=5,
        cursor=first["next_cursor"],
    )["query_result"]

    assert first["next_cursor"]
    assert [item["node"]["id"] for item in first["hits"]] != [
        item["node"]["id"] for item in second["hits"]
    ]
