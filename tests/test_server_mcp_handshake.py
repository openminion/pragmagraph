from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

from pragmagraph.server.backend import ServiceConfig, build_wired_registry
from pragmagraph.server.contracts import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_REQUEST,
    MCP_PROTOCOL_VERSION,
    TOOL_NOT_FOUND_CODE,
    TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE,
    TOOL_UNSUPPORTED_CAPABILITY_CODE,
)
from pragmagraph.server.server import ServerInfo, dispatch, serve_stdio
from pragmagraph.server.tools import SUPPORTED_TOOL_NAMES, ToolRegistry


def _seed_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# Runtime Graph\n", encoding="utf-8")
    (root / "src" / "app.py").write_text(
        "class RuntimeGraph:\n"
        "    pass\n\n"
        "def build_runtime_graph():\n"
        "    return RuntimeGraph()\n",
        encoding="utf-8",
    )


def _registry(tmp_path: Path):
    root = tmp_path / "repo"
    _seed_repo(root)
    return build_wired_registry(ServiceConfig(root_path=str(root), namespace="fixture"))


def test_initialize_returns_protocol_version_and_server_info(tmp_path: Path) -> None:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "clientInfo": {"name": "test"}},
        },
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    assert response["id"] == 1
    result = response["result"]
    assert result["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == "pragmagraph-server"
    assert result["capabilities"]["tools"] == {"listChanged": False}


def test_tools_list_returns_exactly_the_supported_ten(tmp_path: Path) -> None:
    response = dispatch(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    tool_names = {tool["name"] for tool in response["result"]["tools"]}
    assert tool_names == set(SUPPORTED_TOOL_NAMES)


def test_tools_call_capabilities_is_fully_wired(tmp_path: Path) -> None:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "pragmagraph_capabilities", "arguments": {}},
        },
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    content = response["result"]["structuredContent"]
    assert response["result"]["content"][0]["type"] == "text"
    assert content["protocol_version"] == MCP_PROTOCOL_VERSION
    assert content["service"]["startup_mode"] == "root"


def test_tools_call_query_returns_cited_result(tmp_path: Path) -> None:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "pragmagraph_query",
                "arguments": {"text": "RuntimeGraph", "max_results": 5},
            },
        },
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    hits = response["result"]["structuredContent"]["query_result"]["hits"]
    assert hits[0]["node"]["label"] == "RuntimeGraph"


def test_tools_call_banned_semantic_endpoint_returns_typed_refusal(
    tmp_path: Path,
) -> None:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "summarize", "arguments": {}},
        },
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    error = response["error"]
    assert error["code"] == TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE
    assert error["data"]["boundary"] == "anti_llm"


def test_unknown_tool_returns_typed_not_found(tmp_path: Path) -> None:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "pragmagraph_unknown", "arguments": {}},
        },
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    assert response["error"]["code"] == TOOL_NOT_FOUND_CODE


def test_unexpected_tool_failure_returns_jsonrpc_internal_error() -> None:
    registry = ToolRegistry.default()

    def fail() -> dict[str, object]:
        raise RuntimeError("provider unavailable")

    health_schema = next(
        schema for schema in registry.schemas() if schema.name == "pragmagraph_health"
    )
    registry.register(health_schema, fail)
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 61,
            "method": "tools/call",
            "params": {"name": "pragmagraph_health", "arguments": {}},
        },
        registry=registry,
        server_info=ServerInfo(),
    )

    assert response is not None
    assert response["error"]["code"] == JSONRPC_INTERNAL_ERROR
    assert (
        response["error"]["message"] == "tool 'pragmagraph_health' failed unexpectedly"
    )
    assert "data" not in response["error"]
    assert "provider unavailable" not in json.dumps(response)


def test_missing_jsonrpc_version_returns_invalid_request(tmp_path: Path) -> None:
    response = dispatch(
        {"id": 7, "method": "initialize"},
        registry=_registry(tmp_path),
        server_info=ServerInfo(),
    )
    assert response is not None
    assert response["error"]["code"] == JSONRPC_INVALID_REQUEST


def test_stdio_loop_processes_initialize_tools_list_and_query(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    init_msg = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )
    list_msg = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    query_msg = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "pragmagraph_query",
                "arguments": {"text": "RuntimeGraph"},
            },
        }
    )
    stdin = io.BytesIO(
        (init_msg + "\n" + list_msg + "\n" + query_msg + "\n").encode("utf-8")
    )
    stdout = io.BytesIO()
    exit_code = serve_stdio(stdin=stdin, stdout=stdout, registry=registry)
    assert exit_code == 0
    lines = [line for line in stdout.getvalue().decode("utf-8").splitlines() if line]
    assert len(lines) == 3
    init_response = json.loads(lines[0])
    list_response = json.loads(lines[1])
    query_response = json.loads(lines[2])
    assert init_response["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert {tool["name"] for tool in list_response["result"]["tools"]} == set(
        SUPPORTED_TOOL_NAMES
    )
    assert (
        query_response["result"]["structuredContent"]["query_result"]["hits"][0][
            "node"
        ]["label"]
        == "RuntimeGraph"
    )


def test_refresh_on_snapshot_registry_returns_typed_unsupported_capability(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    _seed_repo(root)
    snapshot = tmp_path / "snapshot.json"
    from pragmagraph import index_path, save_snapshot

    save_snapshot(index_path(root, namespace="fixture"), snapshot)
    registry = build_wired_registry(ServiceConfig(snapshot_path=str(snapshot)))
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "pragmagraph_refresh", "arguments": {}},
        },
        registry=registry,
        server_info=ServerInfo(),
    )
    assert response is not None
    assert response["error"]["code"] == TOOL_UNSUPPORTED_CAPABILITY_CODE


def test_serve_stdio_subprocess_completes_initialize_handshake(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    repo = tmp_path / "repo"
    _seed_repo(repo)
    env = {"PYTHONPATH": str(root / "src")}
    init_msg = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph.server",
            "serve-stdio",
            "--root",
            str(repo),
        ],
        input=init_msg + "\n",
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, "serve-stdio produced no response"
    response = json.loads(lines[0])
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION


def test_mcp_consumer_smoke_starts_server_and_calls_investigate(
    tmp_path: Path,
) -> None:
    from pragmagraph import index_path, save_snapshot
    from pragmagraph.server.smoke import run_mcp_consumer_smoke

    repo = tmp_path / "repo"
    _seed_repo(repo)
    snapshot = tmp_path / "snapshot.json"
    save_snapshot(index_path(repo, namespace="smoke"), snapshot)

    payload = run_mcp_consumer_smoke(snapshot=str(snapshot), query="RuntimeGraph")

    assert payload["schema_version"] == "pragmagraph.mcp_consumer_smoke.v1alpha1"
    assert payload["ok"] is True
    assert payload["source"] == "snapshot"
    assert payload["protocol_version"] == MCP_PROTOCOL_VERSION
    assert "pragmagraph_investigate" in payload["tool_names"]
    assert payload["investigation"]["boundary"] == "observed_facts_only"
