"""Minimal stdio MCP server bootstrap for the pragmagraph-server runtime."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, BinaryIO, Mapping

from pragmagraph import __version__
from pragmagraph.server.contracts import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    MCP_PROTOCOL_VERSION,
    PragmaGraphServerError,
    TOOL_NOT_FOUND_CODE,
)
from pragmagraph.server.tools import ToolRegistry, ToolSchema


@dataclass(frozen=True)
class ServerInfo:
    name: str = "pragmagraph-server"
    version: str = __version__


def _ok_response(request_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": dict(result)}


def _err_response(
    request_id: Any, code: int, message: str, details: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": int(code), "message": str(message)}
    if details:
        error["data"] = dict(details)
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _schema_to_payload(schema: ToolSchema) -> dict[str, Any]:
    return {
        "name": schema.name,
        "description": schema.description,
        "inputSchema": dict(schema.input_schema),
        "outputSchema": dict(schema.output_schema),
    }


def _handle_initialize(
    request_id: Any,
    params: Mapping[str, Any],
    server_info: ServerInfo,
    registry: ToolRegistry,
) -> dict[str, Any]:
    requested_version = str(params.get("protocolVersion") or "")
    capabilities = {"tools": {"listChanged": False}}
    if registry.resources is not None:
        capabilities["resources"] = {"listChanged": False}
    return _ok_response(
        request_id,
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": capabilities,
            "serverInfo": {"name": server_info.name, "version": server_info.version},
            "negotiated": {
                "client_requested": requested_version,
                "server_offered": MCP_PROTOCOL_VERSION,
            },
        },
    )


def _handle_tools_list(request_id: Any, registry: ToolRegistry) -> dict[str, Any]:
    return _ok_response(
        request_id,
        {"tools": [_schema_to_payload(schema) for schema in registry.schemas()]},
    )


def _handle_tools_call(
    request_id: Any,
    params: Mapping[str, Any],
    registry: ToolRegistry,
) -> dict[str, Any]:
    name = str(params.get("name") or "")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, Mapping):
        return _err_response(
            request_id,
            JSONRPC_INVALID_PARAMS,
            "tools/call: 'arguments' must be an object",
        )
    try:
        handler = registry.get_handler(name)
    except KeyError:
        return _err_response(
            request_id,
            TOOL_NOT_FOUND_CODE,
            f"tool {name!r} is not registered",
            {"tool_name": name},
        )
    except PragmaGraphServerError as err:
        return _err_response(request_id, err.code, str(err), err.details)
    try:
        result = handler(**dict(arguments))
    except PragmaGraphServerError as err:
        return _err_response(request_id, err.code, str(err), err.details)
    except ValueError as err:
        return _err_response(request_id, JSONRPC_INVALID_PARAMS, str(err))
    except Exception:
        return _err_response(
            request_id,
            JSONRPC_INTERNAL_ERROR,
            f"tool {name!r} failed unexpectedly",
        )
    structured = dict(result)
    return _ok_response(
        request_id,
        {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(structured, sort_keys=True, default=str),
                }
            ],
            "structuredContent": structured,
        },
    )


def _handle_resources_list(request_id: Any, registry: ToolRegistry) -> dict[str, Any]:
    resources = registry.resources
    payload = (
        []
        if resources is None
        else [item.to_dict() for item in resources.list_resources()]
    )
    return _ok_response(request_id, {"resources": payload})


def _handle_resource_templates_list(
    request_id: Any,
    registry: ToolRegistry,
) -> dict[str, Any]:
    resources = registry.resources
    payload = [] if resources is None else list(resources.list_templates())
    return _ok_response(request_id, {"resourceTemplates": payload})


def _handle_resources_read(
    request_id: Any,
    params: Mapping[str, Any],
    registry: ToolRegistry,
) -> dict[str, Any]:
    uri = params.get("uri")
    if not isinstance(uri, str) or not uri:
        return _err_response(
            request_id, JSONRPC_INVALID_PARAMS, "resources/read requires uri"
        )
    if registry.resources is None:
        return _err_response(
            request_id, JSONRPC_INVALID_REQUEST, "resources are not wired"
        )
    try:
        return _ok_response(request_id, registry.resources.read(uri))
    except ValueError as exc:
        return _err_response(request_id, JSONRPC_INVALID_PARAMS, str(exc), {"uri": uri})


def dispatch(
    message: Mapping[str, Any],
    *,
    registry: ToolRegistry,
    server_info: ServerInfo,
) -> dict[str, Any] | None:
    if not isinstance(message, Mapping):
        return _err_response(None, JSONRPC_INVALID_REQUEST, "request must be an object")
    if message.get("jsonrpc") != "2.0":
        return _err_response(
            message.get("id"), JSONRPC_INVALID_REQUEST, "missing jsonrpc=2.0"
        )
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if not isinstance(params, Mapping):
        return _err_response(
            request_id, JSONRPC_INVALID_PARAMS, "params must be an object"
        )
    is_notification = "id" not in message
    if method == "initialize":
        return _handle_initialize(request_id, params, server_info, registry)
    if method in {"initialized", "notifications/initialized"}:
        return None if is_notification else _ok_response(request_id, {})
    if method == "tools/list":
        return _handle_tools_list(request_id, registry)
    if method == "tools/call":
        return _handle_tools_call(request_id, params, registry)
    if method == "resources/list":
        return _handle_resources_list(request_id, registry)
    if method == "resources/templates/list":
        return _handle_resource_templates_list(request_id, registry)
    if method == "resources/read":
        return _handle_resources_read(request_id, params, registry)
    if method == "ping":
        return _ok_response(request_id, {})
    if is_notification:
        return None
    return _err_response(
        request_id,
        JSONRPC_METHOD_NOT_FOUND,
        f"method {method!r} is not supported by pragmagraph-server v1",
    )


def serve_stdio(
    *,
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | None = None,
    registry: ToolRegistry | None = None,
    server_info: ServerInfo | None = None,
) -> int:
    in_stream = stdin if stdin is not None else sys.stdin.buffer
    out_stream = stdout if stdout is not None else sys.stdout.buffer
    resolved_registry = registry if registry is not None else ToolRegistry.default()
    resolved_info = server_info if server_info is not None else ServerInfo()
    while True:
        raw_line = in_stream.readline()
        if not raw_line:
            return 0
        try:
            text = raw_line.decode("utf-8").strip()
        except UnicodeDecodeError:
            _write_response(
                out_stream, _err_response(None, JSONRPC_PARSE_ERROR, "non-utf-8 line")
            )
            continue
        if not text:
            continue
        try:
            message = json.loads(text)
        except json.JSONDecodeError as err:
            _write_response(
                out_stream,
                _err_response(
                    None,
                    JSONRPC_PARSE_ERROR,
                    f"invalid JSON: {err.msg} (line {err.lineno} col {err.colno})",
                ),
            )
            continue
        response = dispatch(
            message, registry=resolved_registry, server_info=resolved_info
        )
        if response is not None:
            _write_response(out_stream, response)


def _write_response(out_stream: BinaryIO, response: Mapping[str, Any]) -> None:
    payload = json.dumps(response, ensure_ascii=False) + "\n"
    out_stream.write(payload.encode("utf-8"))
    out_stream.flush()


__all__ = ["ServerInfo", "dispatch", "serve_stdio"]
