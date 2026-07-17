from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from pragmagraph.adapters import index_path
from pragmagraph.interchange import load_native_scip
from pragmagraph.server.backend import ServiceConfig, build_wired_registry
from pragmagraph.server.server import ServerInfo, dispatch
from pragmagraph.server.tools import ToolRegistry
from pragmagraph.storage import save_snapshot
from .scip_fixtures import TYPESCRIPT_SCIP


def _call(registry, method: str, params=None):
    return dispatch(
        {"jsonrpc": "2.0", "id": method, "method": method, "params": params or {}},
        registry=registry,
        server_info=ServerInfo(),
    )


def test_mcp_resources_list_templates_and_read_loaded_state(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "service.py").write_text("def serve():\n    return 1\n")
    snapshot_path = tmp_path / "snapshot.json"
    snapshot = index_path(root, namespace="resources")
    save_snapshot(snapshot, snapshot_path)
    registry = build_wired_registry(ServiceConfig(snapshot_path=str(snapshot_path)))

    initialized = _call(registry, "initialize", {"protocolVersion": "2025-06-18"})
    listed = _call(registry, "resources/list")
    templates = _call(registry, "resources/templates/list")
    status = _call(registry, "resources/read", {"uri": "pragma://status"})
    node_id = snapshot.nodes[0].id
    node = _call(
        registry, "resources/read", {"uri": f"pragma://node/{quote(node_id, safe='')}"}
    )

    assert initialized["result"]["capabilities"]["resources"] == {"listChanged": False}
    assert [item["uri"] for item in listed["result"]["resources"]] == [
        "pragma://status",
        "pragma://snapshot",
        "pragma://report",
        "pragma://precise-ingestion",
    ]
    assert (
        templates["result"]["resourceTemplates"][0]["uriTemplate"]
        == "pragma://node/{node_id}"
    )
    status_payload = json.loads(status["result"]["contents"][0]["text"])
    node_payload = json.loads(node["result"]["contents"][0]["text"])
    assert status_payload["capabilities"]["namespace"] == "resources"
    assert node_payload["id"] == node_id


def test_mcp_precise_ingestion_resource_reports_loaded_state(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "precise.json"
    save_snapshot(load_native_scip(TYPESCRIPT_SCIP).snapshot, snapshot_path)
    registry = build_wired_registry(ServiceConfig(snapshot_path=str(snapshot_path)))

    response = _call(
        registry,
        "resources/read",
        {"uri": "pragma://precise-ingestion"},
    )
    payload = json.loads(response["result"]["contents"][0]["text"])

    assert payload["loaded"] is True
    assert payload["report"]["producer"]["name"] == "scip-typescript"


def test_initialize_omits_resources_when_registry_is_not_wired() -> None:
    initialized = _call(
        ToolRegistry.default(),
        "initialize",
        {"protocolVersion": "2025-06-18"},
    )

    assert initialized["result"]["capabilities"] == {"tools": {"listChanged": False}}
