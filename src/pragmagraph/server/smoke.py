"""Short-lived MCP stdio smoke for package-local consumer proof."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from pragmagraph.server.contracts import MCP_PROTOCOL_VERSION

MCP_SMOKE_SCHEMA_VERSION = "pragmagraph.mcp_consumer_smoke.v1alpha1"


def run_mcp_consumer_smoke(
    *,
    snapshot: str = "",
    root: str = "",
    namespace: str = "default",
    query: str = "RuntimeGraph",
    timeout: int = 15,
) -> dict[str, Any]:
    """Start pragmagraph-server once and prove basic MCP tool use."""
    command = _server_command(snapshot=snapshot, root=root, namespace=namespace)
    messages = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": MCP_PROTOCOL_VERSION},
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "pragmagraph_investigate",
                "arguments": {"text": query, "preset": "search", "max_results": 3},
            },
        },
    )
    proc = subprocess.run(
        command,
        input="".join(
            json.dumps(message, sort_keys=True) + "\n" for message in messages
        ),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    responses = _response_lines(proc.stdout)
    tool_names = _tool_names(responses)
    investigation = _structured_content(responses, 3).get("investigation", {})
    diagnostics = []
    if proc.returncode != 0:
        diagnostics.append("server_exit_nonzero")
    if len(responses) != 3:
        diagnostics.append("unexpected_response_count")
    if "pragmagraph_investigate" not in tool_names:
        diagnostics.append("investigate_tool_not_listed")
    if not investigation:
        diagnostics.append("investigate_tool_no_structured_content")
    return {
        "schema_version": MCP_SMOKE_SCHEMA_VERSION,
        "boundary": "observed_facts_only",
        "ok": not diagnostics,
        "source": "snapshot" if snapshot else "root",
        "command": command,
        "returncode": proc.returncode,
        "protocol_version": _protocol_version(responses),
        "tool_names": sorted(tool_names),
        "called_tool": "pragmagraph_investigate",
        "investigation": investigation,
        "diagnostics": diagnostics,
    }


def _server_command(*, snapshot: str, root: str, namespace: str) -> list[str]:
    command = [sys.executable, "-m", "pragmagraph.server", "serve-stdio"]
    if snapshot:
        command.extend(["--snapshot", snapshot])
    else:
        command.extend(["--root", root or "."])
        command.extend(["--namespace", namespace])
    return command


def _response_lines(stdout: str) -> list[dict[str, Any]]:
    responses = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            responses.append(payload)
    return responses


def _protocol_version(responses: list[dict[str, Any]]) -> str:
    result = _result_by_id(responses, 1)
    return str(result.get("protocolVersion", "") or "")


def _tool_names(responses: list[dict[str, Any]]) -> set[str]:
    result = _result_by_id(responses, 2)
    tools = result.get("tools") or []
    return {
        str(tool.get("name", "") or "")
        for tool in tools
        if isinstance(tool, dict) and tool.get("name")
    }


def _structured_content(
    responses: list[dict[str, Any]], request_id: int
) -> dict[str, Any]:
    result = _result_by_id(responses, request_id)
    content = result.get("structuredContent") or {}
    return dict(content) if isinstance(content, dict) else {}


def _result_by_id(responses: list[dict[str, Any]], request_id: int) -> dict[str, Any]:
    for response in responses:
        if response.get("id") == request_id and isinstance(
            response.get("result"), dict
        ):
            return dict(response["result"])
    return {}


__all__ = ["MCP_SMOKE_SCHEMA_VERSION", "run_mcp_consumer_smoke"]
