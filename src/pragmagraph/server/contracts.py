"""MCP protocol constants and error types for the pragmagraph-server runtime."""

from __future__ import annotations

from typing import Any

# Pin to a published MCP protocol version. Negotiation at handshake time may
# downgrade to a floor; the bounded v1 runtime advertises one supported version.
MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_PROTOCOL_VERSION_FLOOR = "2025-03-26"

# JSON-RPC 2.0 error codes used by the runtime. Public surface so contract
# tests and downstream consumers can assert on exact codes.
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603

# Tool-call failure codes specific to the pragmagraph-server surface.
TOOL_NOT_FOUND_CODE = -32001
TOOL_BACKEND_NOT_WIRED_CODE = -32010
TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE = -32020
TOOL_SERVICE_ERROR_CODE = -32030
TOOL_UNSUPPORTED_CAPABILITY_CODE = -32040


class PragmaGraphServerError(RuntimeError):
    """Base error for pragmagraph-server runtime failures."""

    def __init__(
        self,
        message: str,
        *,
        code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = int(code)
        self.details = dict(details or {})


class BackendNotWiredError(PragmaGraphServerError):
    """Raised when a registered tool has no backend wired yet.

    The default registry ships typed contracts first. Until a live
    `LocalQueryService` is bound through `build_wired_registry()`, data
    operation tools raise this error with a deterministic JSON-RPC payload.
    """

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"tool {tool_name!r} has no backend wired yet",
            code=TOOL_BACKEND_NOT_WIRED_CODE,
            details={"tool_name": tool_name, "blocker": "build_wired_registry"},
        )
        self.tool_name = tool_name


class SemanticEndpointRefusedError(PragmaGraphServerError):
    """Raised on attempts to invoke explicitly banned semantic endpoints.

    The anti-LLM boundary forbids runtime-owned summarize/classify/extract
    endpoints. Any incoming tool call whose name matches the banned set is
    deterministically refused with this error rather than being silently
    routed away.
    """

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            (
                f"tool {tool_name!r} is a banned semantic endpoint; runtime "
                "must remain plumbing-only per the PragmaGraph observed-fact boundary"
            ),
            code=TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE,
            details={"tool_name": tool_name, "boundary": "anti_llm"},
        )
        self.tool_name = tool_name


class ServiceInvocationError(PragmaGraphServerError):
    """Raised when the public package service returns a typed failure."""

    def __init__(
        self,
        tool_name: str,
        *,
        service_code: str,
        service_message: str,
        service_details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"tool {tool_name!r} failed through pragmagraph.service: {service_message}",
            code=TOOL_SERVICE_ERROR_CODE,
            details={
                "tool_name": tool_name,
                "service_error_code": service_code,
                "service_details": dict(service_details or {}),
            },
        )
        self.tool_name = tool_name


class UnsupportedCapabilityError(PragmaGraphServerError):
    """Raised when a current server instance does not support a tool capability."""

    def __init__(
        self,
        tool_name: str,
        *,
        capability: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = dict(details or {})
        payload["tool_name"] = tool_name
        payload["capability"] = capability
        super().__init__(
            f"tool {tool_name!r} is unavailable because capability {capability!r} "
            "is not supported by the current server instance",
            code=TOOL_UNSUPPORTED_CAPABILITY_CODE,
            details=payload,
        )
        self.tool_name = tool_name


__all__ = [
    "MCP_PROTOCOL_VERSION",
    "MCP_PROTOCOL_VERSION_FLOOR",
    "JSONRPC_PARSE_ERROR",
    "JSONRPC_INVALID_REQUEST",
    "JSONRPC_METHOD_NOT_FOUND",
    "JSONRPC_INVALID_PARAMS",
    "JSONRPC_INTERNAL_ERROR",
    "TOOL_NOT_FOUND_CODE",
    "TOOL_BACKEND_NOT_WIRED_CODE",
    "TOOL_SEMANTIC_ENDPOINT_REFUSED_CODE",
    "TOOL_SERVICE_ERROR_CODE",
    "TOOL_UNSUPPORTED_CAPABILITY_CODE",
    "PragmaGraphServerError",
    "BackendNotWiredError",
    "SemanticEndpointRefusedError",
    "ServiceInvocationError",
    "UnsupportedCapabilityError",
]
