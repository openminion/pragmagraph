from __future__ import annotations

import pytest

from pragmagraph.server.contracts import (
    BackendNotWiredError,
    SemanticEndpointRefusedError,
    TOOL_BACKEND_NOT_WIRED_CODE,
    TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE,
)
from pragmagraph.server.tools import (
    BANNED_SEMANTIC_TOOL_NAMES,
    SUPPORTED_TOOL_NAMES,
    ToolRegistry,
    ToolSchema,
)


def test_supported_tool_set_is_exactly_the_bounded_tools() -> None:
    assert SUPPORTED_TOOL_NAMES == (
        "pragmagraph_capabilities",
        "pragmagraph_health",
        "pragmagraph_query",
        "pragmagraph_explain",
        "pragmagraph_neighborhood",
        "pragmagraph_path",
        "pragmagraph_report",
        "pragmagraph_export",
        "pragmagraph_graphify_export",
        "pragmagraph_investigate",
        "pragmagraph_refresh",
    )


def test_default_registry_registers_exactly_the_supported_tools() -> None:
    registry = ToolRegistry.default()
    assert registry.names() == tuple(sorted(SUPPORTED_TOOL_NAMES))


def test_banned_semantic_endpoints_are_a_nonempty_closed_set() -> None:
    assert isinstance(BANNED_SEMANTIC_TOOL_NAMES, frozenset)
    for required in ("summarize", "classify", "extract_claims", "infer_intent"):
        assert required in BANNED_SEMANTIC_TOOL_NAMES
    for required in (
        "pragmagraph_summarize",
        "pragmagraph_classify",
        "pragmagraph_extract_claims",
        "pragmagraph_infer_intent",
    ):
        assert required in BANNED_SEMANTIC_TOOL_NAMES
    assert set(SUPPORTED_TOOL_NAMES).isdisjoint(BANNED_SEMANTIC_TOOL_NAMES)


@pytest.mark.parametrize("banned_name", sorted(BANNED_SEMANTIC_TOOL_NAMES))
def test_registry_refuses_to_register_banned_semantic_tools(banned_name: str) -> None:
    registry = ToolRegistry()
    schema = ToolSchema(
        name=banned_name,
        description="anti-LLM lock violation attempt",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    with pytest.raises(SemanticEndpointRefusedError) as excinfo:
        registry.register(schema, lambda **_: {})
    assert excinfo.value.code == TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE


def test_registry_refuses_to_register_unknown_tools() -> None:
    registry = ToolRegistry()
    schema = ToolSchema(
        name="pragmagraph_invent_a_new_tool",
        description="surface-widening attempt",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    with pytest.raises(ValueError, match="not in the bounded v1 supported set"):
        registry.register(schema, lambda **_: {})


def test_registry_get_handler_for_banned_name_raises_typed_refusal() -> None:
    registry = ToolRegistry.default()
    with pytest.raises(SemanticEndpointRefusedError):
        registry.get_handler("summarize")


def test_data_op_handlers_raise_backend_not_wired_until_wired_registry() -> None:
    registry = ToolRegistry.default()
    handler = registry.get_handler("pragmagraph_query")
    with pytest.raises(BackendNotWiredError) as excinfo:
        handler(text="RuntimeGraph")
    assert excinfo.value.code == TOOL_BACKEND_NOT_WIRED_CODE
    assert excinfo.value.details == {
        "tool_name": "pragmagraph_query",
        "blocker": "build_wired_registry",
    }


def test_capabilities_handler_returns_typed_payload_without_backend() -> None:
    registry = ToolRegistry.default()
    handler = registry.get_handler("pragmagraph_capabilities")
    payload = handler()
    assert payload["protocol_version"] == "2025-06-18"
    assert payload["service"]["wired"] is False
    assert set(payload["supported_tools"]) == set(SUPPORTED_TOOL_NAMES)


def test_each_supported_tool_has_typed_input_and_output_schema() -> None:
    registry = ToolRegistry.default()
    for schema in registry.schemas():
        assert schema.input_schema.get("type") == "object"
        assert schema.output_schema.get("type") == "object"
        assert schema.description
