"""Typed MCP tool surface for the bounded pragmagraph-server v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from pragmagraph import __version__
from pragmagraph.server.contracts import (
    BackendNotWiredError,
    SemanticEndpointRefusedError,
)
from pragmagraph.server.resources import ResourceRegistry


SUPPORTED_TOOL_NAMES: tuple[str, ...] = (
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

BANNED_SEMANTIC_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "summarize",
        "classify",
        "extract_claims",
        "infer_intent",
        "recommend_refactor",
        "pragmagraph_summarize",
        "pragmagraph_classify",
        "pragmagraph_extract_claims",
        "pragmagraph_infer_intent",
        "pragmagraph_recommend_refactor",
    }
)


def _query_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "node_ids": {"type": "array", "items": {"type": "string"}},
            "max_results": {"type": "integer", "minimum": 1},
            "include_edges": {"type": "boolean"},
            "cursor": {"type": "string"},
            "max_examined": {"type": "integer", "minimum": 1},
        },
        "additionalProperties": False,
    }


@dataclass(frozen=True)
class ToolSchema:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]


_TOOL_SCHEMAS: tuple[ToolSchema, ...] = (
    ToolSchema(
        name="pragmagraph_capabilities",
        description="Return server and package capability metadata.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": [
                "protocol_version",
                "server_name",
                "server_version",
                "service",
                "supported_tools",
            ],
            "properties": {
                "protocol_version": {"type": "string"},
                "server_name": {"type": "string"},
                "server_version": {"type": "string"},
                "service": {"type": "object"},
                "supported_tools": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_health",
        description="Return deterministic package health metadata.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["health"],
            "properties": {"health": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_query",
        description="Run deterministic structural query.",
        input_schema=_query_input_schema(),
        output_schema={
            "type": "object",
            "required": ["query_result"],
            "properties": {"query_result": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_explain",
        description="Run deterministic query with explanation-bearing hits.",
        input_schema=_query_input_schema(),
        output_schema={
            "type": "object",
            "required": ["query_result"],
            "properties": {"query_result": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_neighborhood",
        description="Inspect a bounded neighborhood around one node.",
        input_schema={
            "type": "object",
            "required": ["node_id"],
            "properties": {
                "node_id": {"type": "string"},
                "depth": {"type": "integer", "minimum": 1},
                "max_results": {"type": "integer", "minimum": 1},
                "edge_kinds": {"type": "array", "items": {"type": "string"}},
                "node_kinds": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["neighborhood"],
            "properties": {"neighborhood": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_path",
        description="Inspect a bounded path between two graph nodes.",
        input_schema={
            "type": "object",
            "required": ["source_id", "target_id"],
            "properties": {
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
                "max_hops": {"type": "integer", "minimum": 1},
                "edge_kinds": {"type": "array", "items": {"type": "string"}},
                "node_kinds": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_report",
        description="Build deterministic structural report output.",
        input_schema={
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "minimum": 1},
                "format": {"type": "string", "enum": ["json", "markdown"]},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["report"],
            "properties": {"report": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_export",
        description="Export DOT or Mermaid graph text.",
        input_schema={
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["dot", "mermaid"]},
                "profile": {
                    "type": "string",
                    "enum": ["full", "no_content", "no_identities", "portable"],
                },
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["export"],
            "properties": {"export": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_graphify_export",
        description="Emit deterministic Graphify-shaped JSON.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["graphify_export"],
            "properties": {"graphify_export": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_investigate",
        description="Build a guided observed-fact investigation bundle.",
        input_schema={
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string"},
                "preset": {
                    "type": "string",
                    "enum": [
                        "search",
                        "file_map",
                        "symbol_map",
                        "doc_links",
                        "changed_recently",
                        "orphans",
                        "high_degree",
                    ],
                },
                "max_results": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["investigation"],
            "properties": {"investigation": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
    ToolSchema(
        name="pragmagraph_refresh",
        description="Run explicit refresh for a root-backed service session.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["refresh"],
            "properties": {"refresh": {"type": "object"}},
            "additionalProperties": False,
        },
    ),
)


ToolHandler = Callable[..., Mapping[str, Any]]


def _backend_not_wired_handler(tool_name: str) -> ToolHandler:
    def _handler(**_kwargs: Any) -> Mapping[str, Any]:
        raise BackendNotWiredError(tool_name)

    return _handler


def _unwired_capabilities_handler() -> ToolHandler:
    def _handler(**_kwargs: Any) -> Mapping[str, Any]:
        return {
            "protocol_version": "2025-06-18",
            "server_name": "pragmagraph-server",
            "server_version": __version__,
            "service": {"wired": False, "startup_mode": "unconfigured"},
            "supported_tools": list(SUPPORTED_TOOL_NAMES),
        }

    return _handler


@dataclass
class ToolRegistry:
    _handlers: dict[str, ToolHandler] = field(default_factory=dict)
    _schemas: dict[str, ToolSchema] = field(default_factory=dict)
    resources: ResourceRegistry | None = None

    @classmethod
    def default(cls) -> "ToolRegistry":
        registry = cls()
        for schema in _TOOL_SCHEMAS:
            if schema.name == "pragmagraph_capabilities":
                handler = _unwired_capabilities_handler()
            else:
                handler = _backend_not_wired_handler(schema.name)
            registry.register(schema, handler)
        return registry

    def register(self, schema: ToolSchema, handler: ToolHandler) -> None:
        if schema.name in BANNED_SEMANTIC_TOOL_NAMES:
            raise SemanticEndpointRefusedError(schema.name)
        if schema.name not in SUPPORTED_TOOL_NAMES:
            raise ValueError(
                f"tool {schema.name!r} is not in the bounded v1 supported set; "
                "widening requires a spec update"
            )
        self._handlers[schema.name] = handler
        self._schemas[schema.name] = schema

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers.keys()))

    def schemas(self) -> tuple[ToolSchema, ...]:
        return tuple(self._schemas[name] for name in sorted(self._schemas.keys()))

    def get_handler(self, name: str) -> ToolHandler:
        if name in BANNED_SEMANTIC_TOOL_NAMES:
            raise SemanticEndpointRefusedError(name)
        if name not in self._handlers:
            raise KeyError(name)
        return self._handlers[name]


__all__ = [
    "BANNED_SEMANTIC_TOOL_NAMES",
    "SUPPORTED_TOOL_NAMES",
    "ToolHandler",
    "ToolRegistry",
    "ToolSchema",
]
