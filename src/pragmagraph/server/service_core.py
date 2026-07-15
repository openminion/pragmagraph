"""Canonical request/response key owners for pragmagraph-server transport payloads."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from pragmagraph.server.tools import SUPPORTED_TOOL_NAMES


REQUEST_PAYLOAD_KEYS: Mapping[str, tuple[str, ...]] = {
    "pragmagraph_capabilities": (),
    "pragmagraph_health": (),
    "pragmagraph_query": (
        "text",
        "node_ids",
        "max_results",
        "include_edges",
        "cursor",
        "max_examined",
    ),
    "pragmagraph_explain": (
        "text",
        "node_ids",
        "max_results",
        "include_edges",
        "cursor",
        "max_examined",
    ),
    "pragmagraph_neighborhood": (
        "node_id",
        "depth",
        "max_results",
        "edge_kinds",
        "node_kinds",
    ),
    "pragmagraph_path": (
        "source_id",
        "target_id",
        "max_hops",
        "edge_kinds",
        "node_kinds",
    ),
    "pragmagraph_report": ("top_n", "format"),
    "pragmagraph_export": ("format", "profile"),
    "pragmagraph_graphify_export": (),
    "pragmagraph_refresh": (),
}


RESPONSE_PAYLOAD_KEYS: Mapping[str, tuple[str, ...]] = {
    "pragmagraph_capabilities": (
        "protocol_version",
        "server_name",
        "server_version",
        "service",
        "supported_tools",
    ),
    "pragmagraph_health": ("health",),
    "pragmagraph_query": ("query_result",),
    "pragmagraph_explain": ("query_result",),
    "pragmagraph_neighborhood": ("neighborhood",),
    "pragmagraph_path": ("path",),
    "pragmagraph_report": ("report",),
    "pragmagraph_export": ("export",),
    "pragmagraph_graphify_export": ("graphify_export",),
    "pragmagraph_refresh": ("refresh",),
}


def to_json_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def assert_request_keys_subset(tool_name: str, payload_keys: set[str]) -> None:
    if tool_name not in REQUEST_PAYLOAD_KEYS:
        raise ValueError(
            f"unknown tool name {tool_name!r}; not in SUPPORTED_TOOL_NAMES"
        )
    allowed = set(REQUEST_PAYLOAD_KEYS[tool_name])
    extras = payload_keys - allowed
    if extras:
        raise ValueError(
            f"tool {tool_name!r}: unknown request fields {sorted(extras)}; "
            f"allowed: {sorted(allowed)}"
        )


def canonical_response_keys(tool_name: str) -> tuple[str, ...]:
    if tool_name not in RESPONSE_PAYLOAD_KEYS:
        raise ValueError(
            f"unknown tool name {tool_name!r}; not in SUPPORTED_TOOL_NAMES"
        )
    return RESPONSE_PAYLOAD_KEYS[tool_name]


def _verify_registry_alignment() -> None:
    supported = set(SUPPORTED_TOOL_NAMES)
    if set(REQUEST_PAYLOAD_KEYS) != supported:
        raise RuntimeError("REQUEST_PAYLOAD_KEYS drift vs SUPPORTED_TOOL_NAMES")
    if set(RESPONSE_PAYLOAD_KEYS) != supported:
        raise RuntimeError("RESPONSE_PAYLOAD_KEYS drift vs SUPPORTED_TOOL_NAMES")


_verify_registry_alignment()


__all__ = [
    "REQUEST_PAYLOAD_KEYS",
    "RESPONSE_PAYLOAD_KEYS",
    "assert_request_keys_subset",
    "canonical_response_keys",
    "to_json_dict",
]
