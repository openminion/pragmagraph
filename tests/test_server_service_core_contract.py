from __future__ import annotations

import inspect

import pytest

from pragmagraph.server.contracts import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    MCP_PROTOCOL_VERSION,
    TOOL_BACKEND_NOT_WIRED_CODE,
    TOOL_NOT_FOUND_CODE,
    TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE,
    TOOL_SERVICE_ERROR_CODE,
    TOOL_UNSUPPORTED_CAPABILITY_CODE,
)
from pragmagraph.server.service_core import (
    REQUEST_PAYLOAD_KEYS,
    RESPONSE_PAYLOAD_KEYS,
    assert_request_keys_subset,
    canonical_response_keys,
)
from pragmagraph.server.tools import (
    BANNED_SEMANTIC_TOOL_NAMES,
    SUPPORTED_TOOL_NAMES,
    ToolRegistry,
)


def test_request_keys_cover_every_supported_tool() -> None:
    assert set(REQUEST_PAYLOAD_KEYS.keys()) == set(SUPPORTED_TOOL_NAMES)


def test_response_keys_cover_every_supported_tool() -> None:
    assert set(RESPONSE_PAYLOAD_KEYS.keys()) == set(SUPPORTED_TOOL_NAMES)


def test_no_banned_name_appears_in_request_or_response_keys() -> None:
    for banned in BANNED_SEMANTIC_TOOL_NAMES:
        assert banned not in REQUEST_PAYLOAD_KEYS
        assert banned not in RESPONSE_PAYLOAD_KEYS


def test_request_envelope_matches_backend_handler_kwargs() -> None:
    registry = ToolRegistry.default()
    schema_by_name = {schema.name: schema for schema in registry.schemas()}
    for tool_name, allowed in REQUEST_PAYLOAD_KEYS.items():
        schema = schema_by_name[tool_name]
        assert set(schema.input_schema.get("properties", {}).keys()) == set(allowed)


def test_jsonrpc_codes_are_stable_integers() -> None:
    assert JSONRPC_PARSE_ERROR == -32700
    assert JSONRPC_INVALID_REQUEST == -32600
    assert JSONRPC_METHOD_NOT_FOUND == -32601
    assert JSONRPC_INVALID_PARAMS == -32602
    assert JSONRPC_INTERNAL_ERROR == -32603


def test_pragmagraph_tool_codes_are_stable_integers() -> None:
    assert TOOL_NOT_FOUND_CODE == -32001
    assert TOOL_BACKEND_NOT_WIRED_CODE == -32010
    assert TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE == -32020
    assert TOOL_SERVICE_ERROR_CODE == -32030
    assert TOOL_UNSUPPORTED_CAPABILITY_CODE == -32040


def test_mcp_protocol_version_is_stable() -> None:
    assert MCP_PROTOCOL_VERSION == "2025-06-18"


def test_assert_request_keys_subset_accepts_canonical_keys() -> None:
    assert_request_keys_subset("pragmagraph_query", {"text", "max_results"})
    assert_request_keys_subset("pragmagraph_report", {"top_n", "format"})
    assert_request_keys_subset("pragmagraph_refresh", set())


def test_assert_request_keys_subset_rejects_unknown_key() -> None:
    with pytest.raises(ValueError):
        assert_request_keys_subset("pragmagraph_query", {"text", "extra_field"})


def test_assert_request_keys_subset_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError):
        assert_request_keys_subset("pragmagraph_summarize", set())


def test_canonical_response_keys_reject_unknown_tool() -> None:
    with pytest.raises(ValueError):
        canonical_response_keys("pragmagraph_summarize")


def test_service_core_module_is_pure_python_no_openminion_import() -> None:
    from pragmagraph.server import service_core

    source = inspect.getsource(service_core)
    assert "openminion" not in source
